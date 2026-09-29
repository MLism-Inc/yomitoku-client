import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from yomitoku_client import parse_table_semantic_parser
from yomitoku_client.studio_form_template import (
    apply_studio_form_template,
    load_studio_form_template,
)


def _template():
    return {
        "kind": "form-template",
        "version": 3,
        "documentName": "申込書",
        "page": {"width": 400, "height": 300},
        "fields": [],
        "structure": {
            "tables": [
                {
                    "id": "studio-table",
                    "normBox": [0.0, 0.0, 1.0, 0.5],
                    "style": "border",
                    "cells": [
                        {
                            "id": "key",
                            "normBox": [0.0, 0.0, 0.2, 0.15],
                            "role": "header",
                            "contents": "氏名",
                        },
                        {
                            "id": "value",
                            "normBox": [0.2, 0.0, 0.5, 0.15],
                            "role": "cell",
                            "contents": "テンプレート作成時の値",
                        },
                    ],
                    "kvItems": [{"id": "kv0", "key": ["key"], "value": "value"}],
                    "grids": [],
                }
            ],
            "paragraphs": [],
        },
    }


def test_apply_studio_template_uses_structure_and_current_ocr(tmp_path):
    path = tmp_path / "studio.template.json"
    path.write_text(json.dumps(_template()), encoding="utf-8")
    template = load_studio_form_template(path)
    data = json.loads((Path(__file__).parent / "data/table_semantic.json").read_text())
    page = parse_table_semantic_parser(data).pages[0]

    applied = apply_studio_form_template(template, page, width=400, height=300)

    assert applied.document_name == "申込書"
    assert applied.tables[0].id == "studio-table"
    assert applied.tables[0].cell_map["key"].contents == "氏名"
    assert applied.tables[0].cell_map["value"].contents == "山田"
    assert applied.tables[0].cell_map["value"].meta["fromTemplate"] is True
    assert applied.to_simple().tables[0].kv_items == {"氏名": "山田"}


def test_studio_template_does_not_copy_a_stale_value(tmp_path):
    template_data = _template()
    template_data["structure"]["tables"][0]["cells"][1]["normBox"] = [
        0.7,
        0.7,
        0.9,
        0.9,
    ]
    path = tmp_path / "studio.template.json"
    path.write_text(json.dumps(template_data), encoding="utf-8")
    template = load_studio_form_template(path)
    data = json.loads((Path(__file__).parent / "data/table_semantic.json").read_text())
    page = parse_table_semantic_parser(data).pages[0]

    applied = apply_studio_form_template(template, page, width=400, height=300)

    assert applied.tables[0].cell_map["value"].contents == ""


def test_studio_template_rejects_unknown_cell_references(tmp_path):
    data = _template()
    data["structure"]["tables"][0]["kvItems"][0]["value"] = "missing"
    path = tmp_path / "studio.template.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValidationError, match="unknown cells"):
        load_studio_form_template(path)
