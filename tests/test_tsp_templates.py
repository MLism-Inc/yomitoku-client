"""Template round trips and multi-page exports using real TSP-shaped data."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from yomitoku_client import parse_table_semantic_parser
from yomitoku_client.tsp_semantics import TableSemanticParserTemplateSchema


@pytest.fixture(params=["dict", "list"])
def document(request):
    data = json.loads((Path(__file__).parent / "data/table_semantic.json").read_text())
    if request.param == "list":
        for table in data["result"][0]["tables"]:
            table["cells"] = list(table["cells"].values())
    return parse_table_semantic_parser(data)


def test_views_preserve_raw_and_resolve_list_cells(document):
    page = document.pages[0]
    raw = deepcopy(page.to_json())
    assert document.to_structured()[0].tables[0].kv_items[0].value == "山田太郎"
    assert document.to_simple()[0].tables[0].kv_items["住所"] == {
        "都道府県": "東京都",
        "市区町村": "千代田区",
    }
    assert page.to_json() == raw


def test_template_roundtrip_and_overrides(document, tmp_path):
    page = document.pages[0]
    path = tmp_path / "template.json"
    page.save_template_json(str(path))
    data = json.loads(path.read_text())
    assert data["meta"]["match_policy"] == "cell_id"
    data["tables"][0]["cells"]["c0"]["contents"] = "お名前"
    data["tables"][0]["cells"]["c0"]["role"] = "header"
    data["tables"][0]["kv_items"] = [{"key": "c0", "value": "c1"}]
    data["tables"][0]["grids"] = []
    path.write_text(json.dumps(data))
    assert page.load_template_json(str(path)) is page
    assert page.to_simple().tables[0].kv_items == {"お名前": "山田太郎"}
    assert page.tables[0].grids == []


def test_template_partial_override_and_no_aliasing(document):
    page = document.pages[0]
    template = page.to_template(include_kv=False, include_grids=False)
    # Parse a dictionary-only cell ID and leave unrelated fields untouched.
    data = template.model_dump()
    data["tables"][0]["cells"] = {"c1": {"contents": ""}}
    page.apply_template(data)
    assert page.tables[0].find_cell_by_id("c1").contents == ""
    assert page.tables[0].find_cell_by_id("c1").role == "cell"
    assert len(page.tables[0].kv_items) == 4
    template = page.to_template()
    page.apply_template(template)
    template.tables[0].kv_items[0].value = "changed"
    assert page.tables[0].kv_items[0].value == "c1"


def test_bbox_template_and_unmatched_table(document):
    page = document.pages[0]
    template = page.to_template(include_kv=False, include_grids=False)
    template.meta.match_policy = "bbox"
    template.tables[0].cells = {"anything": template.tables[0].cells["c1"]}
    template.tables[0].cells["anything"].id = "different-id"
    template.tables[0].cells["anything"].contents = "更新"
    page.apply_template(template)
    assert page.tables[0].find_cell_by_id("c1").contents == "更新"
    template.tables[0].box = [1000, 1000, 2000, 2000]
    template.tables[0].cells["anything"].contents = "not matched"
    page.apply_template(template)
    assert page.tables[0].find_cell_by_id("c1").contents == "更新"


def test_idless_lists_use_bbox_templates(document):
    page = document.pages[0]
    table = page.tables[0]
    table.cells = list(table.cell_map.values())
    for cell in table.cells:
        cell.id = None
    template = page.to_template()
    assert template.meta.match_policy == "bbox"
    template.tables[0].cells["0"].contents = "changed"
    page.apply_template(template)
    assert table.cells[0].contents == "changed"


@pytest.mark.parametrize("output_mode", ["raw", "structured", "simple", "template"])
@pytest.mark.parametrize("mode", ["combine", "separate"])
def test_sparse_page_export(document, tmp_path, mode, output_mode):
    page = document.pages.pop(0)
    page.num_page = 3
    document.pages[3] = page
    path = tmp_path / "result.json"
    result = document.to_json(str(path), mode=mode, output_mode=output_mode)
    saved = json.loads(
        (path if mode == "combine" else tmp_path / "result_page_3.json").read_text()
    )
    assert result[0]["num_page"] == 3
    assert saved == (result if mode == "combine" else result[0])
    if output_mode == "template":
        TableSemanticParserTemplateSchema.model_validate(result[0])


def test_multipage_templates_match_indices_and_validate_before_mutating(
    document, tmp_path
):
    document.pages[2] = document.pages[0].model_copy(deep=True, update={"num_page": 2})
    path = tmp_path / "templates.json"
    document.save_template_json(str(path))
    templates = json.loads(path.read_text())
    templates[0]["tables"][0]["cells"]["c0"]["contents"] = "first"
    templates[1]["tables"][0]["cells"]["c0"]["contents"] = "third"
    path.write_text(json.dumps(list(reversed(templates))))
    document.load_template_json(str(path))
    assert document.pages[0].tables[0].find_cell_by_id("c0").contents == "first"
    assert document.pages[2].tables[0].find_cell_by_id("c0").contents == "third"
    templates[0]["tables"][0]["cells"]["c0"]["contents"] = "must not apply"
    templates[1]["meta"]["match_policy"] = "invalid"
    path.write_text(json.dumps(templates))
    with pytest.raises(ValidationError):
        document.load_template_json(str(path))
    assert document.pages[0].tables[0].find_cell_by_id("c0").contents == "first"


def test_duplicate_cell_ids_are_not_silently_lost(document):
    table = document.pages[0].tables[0]
    cells = list(table.cell_map.values())
    table.cells = [cells[0], cells[0].model_copy()]
    with pytest.raises(ValueError, match="Duplicate cell id"):
        document.to_structured()


@pytest.mark.parametrize("method", ["to_structured", "to_simple"])
def test_page_view_exports_json(document, tmp_path, method):
    view = getattr(document.pages[0], method)()
    path = tmp_path / "nested" / "page.json"
    assert view.to_json(str(path)) == view.model_dump()
    assert json.loads(path.read_text()) == view.model_dump()
