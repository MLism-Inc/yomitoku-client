"""
Tests for the Table Semantic Parser (TSP) models and parser
"""

import json
from pathlib import Path

import pytest

from yomitoku_client import (
    MultiPageDocumentResult,
    MultiPageTableSemanticParserResult,
    parse_table_semantic_parser,
)
from yomitoku_client.cli.utils import parse_model
from yomitoku_client.constants import (
    API_DOCUMENT_ANALYZER,
    API_TABLE_SEMANTIC_PARSER,
)
from yomitoku_client.exceptions import DocumentAnalysisError

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture
def tsp_api_result():
    """Response of the Table Semantic Parser endpoint (one page)"""
    with (DATA_DIR / "table_semantic.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def tsp_document(tsp_api_result):
    return parse_table_semantic_parser(tsp_api_result)


class TestParse:
    def test_parse_builds_pages(self, tsp_document):
        assert isinstance(tsp_document, MultiPageTableSemanticParserResult)
        assert list(tsp_document.pages) == [0]

        page = tsp_document.pages[0]
        assert len(page.tables) == 1
        assert page.paragraphs[0].contents == "以上のとおり申請します。"
        assert page.words[0].content == "山田"

    def test_parse_keeps_table_structure(self, tsp_document):
        table = tsp_document.pages[0].tables[0]

        assert table.id == "t0"
        assert table.style == "border"
        # cells は cell_id をキーにした dict で返る
        assert len(table.cells) == 14
        assert table.cells["c0"].contents == "氏 名"
        assert table.cells["c0"].role == "header"

        # kv_items の key は cell_id の配列、value は cell_id
        assert table.kv_items[0].key == ["c0"]
        assert table.kv_items[0].value == "c1"

        grid = table.grids[0]
        assert (grid.id, grid.n_row, grid.n_col) == ("g0", 3, 2)
        assert grid.col_headers == [["c7"], ["c8"]]
        assert grid.data[1] == ["c9", "c10"]

    def test_parse_assigns_page_index(self, tsp_api_result):
        """Batch Transform 出力には num_page が無いので順序から補う"""
        two_pages = {"result": tsp_api_result["result"] * 2}
        document = parse_table_semantic_parser(two_pages)

        assert sorted(document.pages) == [0, 1]
        assert document.pages[1].num_page == 1

    def test_parse_missing_result(self):
        with pytest.raises(DocumentAnalysisError):
            parse_table_semantic_parser({})

    def test_parse_invalid_schema(self, tsp_api_result):
        """必須フィールドを欠いたレスポンスは弾く"""
        broken = json.loads(json.dumps(tsp_api_result))
        del broken["result"][0]["tables"][0]["cells"]["c0"]["box"]

        with pytest.raises(DocumentAnalysisError):
            parse_table_semantic_parser(broken)

    def test_parse_model_dispatches_on_api(self, tsp_api_result):
        """CLI は --api の値でパーサを切り替える"""
        with (DATA_DIR / "image_pdf.json").open(encoding="utf-8") as f:
            document_result = json.load(f)

        assert isinstance(
            parse_model(tsp_api_result, API_TABLE_SEMANTIC_PARSER),
            MultiPageTableSemanticParserResult,
        )
        assert isinstance(
            parse_model(document_result, API_DOCUMENT_ANALYZER),
            MultiPageDocumentResult,
        )


class TestJsonExport:
    def test_page_to_json_keeps_response(self, tsp_document, tsp_api_result):
        page = tsp_document.pages[0].to_json()
        source = tsp_api_result["result"][0]

        assert page["num_page"] == 0
        assert page["tables"][0]["cells"]["c0"]["contents"] == "氏 名"
        assert len(page["tables"][0]["grids"]) == len(source["tables"][0]["grids"])
        assert [p["contents"] for p in page["paragraphs"]] == [
            p["contents"] for p in source["paragraphs"]
        ]

    def test_to_json_combine(self, tsp_document, tmp_path: Path):
        output_path = tmp_path / "out" / "table.json"
        tsp_document.to_json(output_path=str(output_path))

        saved = json.loads(output_path.read_text(encoding="utf-8"))
        assert isinstance(saved, list)
        assert saved[0]["tables"][0]["id"] == "t0"

    def test_to_json_separate(self, tsp_document, tmp_path: Path):
        output_path = tmp_path / "table.json"
        tsp_document.to_json(output_path=str(output_path), mode="separate")

        page_path = tmp_path / "table_page_0.json"
        assert page_path.exists()
        assert json.loads(page_path.read_text(encoding="utf-8"))["num_page"] == 0

    def test_to_json_page_index(self, tsp_api_result, tmp_path: Path):
        document = parse_table_semantic_parser({"result": tsp_api_result["result"] * 3})
        output_path = tmp_path / "table.json"

        saved = document.to_json(output_path=str(output_path), page_index=[0, 2])

        assert [page["num_page"] for page in saved] == [0, 2]
