"""
Data models for the YomiToku-Pro Table Semantic Parser (TSP) API.

The TSP endpoint (``YOMITOKU_SAGEMAKER_APP=table_semantic_parser``) returns the
semantic structure of every table in a page:

* ``cells``     : detected cells as a list or keyed by cell id (contents / role / span)
* ``kv_items``  : key-value pairs resolved from form-style layouts
* ``grids``     : row/column grids with their column headers

These models mirror the API response so it can be validated and saved as JSON.
Structured/simple views and editable templates are provided without inference dependencies.

The response envelope is the same as the document analyzer
(``{"result": [<page>, ...]}``), so :class:`~yomitoku_client.client.YomitokuClient`
can be used unchanged; only the parsing side differs.
"""

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .models import Word
from .utils import export_results_to_file, make_page_index


class LayoutElement(BaseModel):
    """Layout element (paragraph) detected outside of tables"""

    id: str | None = Field(default=None, description="Element id")
    box: list[int] = Field(description="Bounding box coordinates [x1, y1, x2, y2]")
    score: float | None = Field(default=None, description="Detection score")
    role: str | None = Field(default=None, description="Element role")
    contents: str | None = Field(default=None, description="Text content")


class SemanticCell(BaseModel):
    """Table cell detected by the cell detector"""

    id: str | None = Field(default=None, description="Cell id")
    box: list[int] = Field(description="Bounding box coordinates [x1, y1, x2, y2]")
    contents: str | None = Field(default=None, description="Text content of the cell")
    role: str | None = Field(
        default=None,
        description="Cell role, e.g. ['cell', 'header', 'empty', 'group']",
    )
    row: int | None = Field(default=None, description="Row index")
    col: int | None = Field(default=None, description="Column index")
    row_span: int | None = Field(default=None, description="Number of rows spanned")
    col_span: int | None = Field(default=None, description="Number of columns spanned")
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class KvItem(BaseModel):
    """Key-value item extracted from a form-style table"""

    id: str | None = Field(default=None, description="Key-value item id")
    key: str | list[str] = Field(description="Key cell id(s)")
    value: str = Field(description="Value cell id")
    box: list[int] | None = Field(
        default=None,
        description="Bounding box coordinates [x1, y1, x2, y2]",
    )


class TableGrid(BaseModel):
    """Grid (row/column) representation of a table"""

    id: str | None = Field(default=None, description="Grid id")
    box: list[int] = Field(description="Bounding box coordinates [x1, y1, x2, y2]")
    n_row: int = Field(description="Number of rows")
    n_col: int = Field(description="Number of columns")
    col_headers: list[list[str]] = Field(
        description="Column header cell ids for each column",
    )
    data: list[list[str | None]] = Field(description="Cell ids laid out as a grid")


class SemanticTable(BaseModel):
    """A single table with its cells, key-value items and grids"""

    id: str | None = Field(default=None, description="Table id")
    box: list[int] = Field(description="Bounding box coordinates [x1, y1, x2, y2]")
    style: str = Field(default="border", description="Border style of the table")
    cells: dict[str, SemanticCell] | list[SemanticCell] = Field(
        default_factory=dict,
        description="Cells as a list or a dictionary keyed by cell id",
    )
    kv_items: list[KvItem] = Field(default_factory=list, description="Key-value items")
    grids: list[TableGrid] = Field(default_factory=list, description="Table grids")

    @property
    def cell_map(self) -> dict[str, SemanticCell]:
        """Index cells without changing the raw response's list/dict representation.

        Lists must carry unique IDs to resolve semantic references. ID-less cells
        remain available for bounding-box template matching.
        """
        if isinstance(self.cells, dict):
            return self.cells
        cells = {}
        for cell in self.cells:
            if cell.id is None:
                continue
            if cell.id in cells:
                raise ValueError(f"Duplicate cell id: {cell.id}")
            cells[cell.id] = cell
        return cells

    @property
    def view(self):
        from .tsp_semantics import TableSemanticContentsView

        return TableSemanticContentsView(
            self.model_copy(update={"cells": self.cell_map})
        )

    def find_cell_by_id(self, cell_id: str) -> SemanticCell | None:
        return self.cell_map.get(str(cell_id))

    def safe_contents(self, cell_id: str, ignore_space: bool = True) -> str:
        cell = self.find_cell_by_id(cell_id)
        contents = (cell.contents or "") if cell else ""
        return contents.replace(" ", "") if ignore_space else contents

    def search_cells_by_bbox(self, box: list[int]) -> list[SemanticCell]:
        from .tsp_semantics import overlap_ratio

        cells = self.cells.values() if isinstance(self.cells, dict) else self.cells
        return [
            cell
            for cell in cells
            if cell.role != "group" and overlap_ratio(box, cell.box) > 0.5
        ]


class TableSemanticParserResult(BaseModel):
    """Table semantic parsing result of a single page"""

    num_page: int = Field(default=0, description="Page index in the original document")
    document_name: str | None = Field(
        default=None,
        description="Document title detected in the page",
    )
    tables: list[SemanticTable] = Field(
        default_factory=list,
        description="Tables with their semantic structure",
    )
    paragraphs: list[LayoutElement] = Field(
        default_factory=list,
        description="Paragraphs detected outside of tables",
    )
    words: list[Word] = Field(default_factory=list, description="Detected words")

    def to_json(self) -> dict:
        """
        Convert the page to a JSON-serializable dictionary

        Returns:
            dict: The page as returned by the API, plus ``num_page``
        """
        return self.model_dump()

    def to_dict(self, separator="\n"):
        """テーブルIDごとの構造化情報 (kv_items / grids) を dict で返す。

        kv_items は to_simple と同じく、キーセルの入れ子構造を保った
        階層dictになる (kv_items_to_nested を参照)。同一キーセル列の
        複数 value は separator で結合される。
        """
        results = {}
        for table in self.tables:
            result = {
                "kv_items": table.view.kv_items_to_nested(separator=separator),
                "grids": table.view.grids_to_dict(),
            }
            results[table.id] = result

        return results

    def to_structured(self, separator="\n"):
        """ドキュメント全体を、テキストとセル座標を解決した構造化形に変換する。

        to_dict のkey-value構造に加えて、各エントリに由来セルのIDと座標
        (key_cells / value_cells) を埋め込み、paragraphs も含める。
        """
        from .tsp_semantics import StructuredDocumentSchema, StructuredTableSchema

        tables = []
        for table in self.tables:
            tables.append(
                StructuredTableSchema(
                    id=table.id,
                    box=table.box,
                    style=table.style,
                    kv_items=table.view.kv_items_to_structured(separator=separator),
                    grids=table.view.grids_to_structured(),
                )
            )

        return StructuredDocumentSchema(
            document_name=self.document_name,
            tables=tables,
            paragraphs=self.paragraphs,
        )

    def to_simple(self, separator="\n"):
        """座標などのメタ情報を持たないテキストのみの構造化形に変換する。

        to_structured からセル参照・座標・スコア類を落とした形。
        kv_items はキーセルの入れ子構造を保った階層dictになる
        (kv_items_to_nested を参照)。同一キーの結合挙動は to_structured と
        同一。grid の行内でヘッダテキストが重複する場合は _0/_1 の
        インデックスを付与して値の消失を防ぐ。
        """
        from .tsp_semantics import (
            SimpleDocumentSchema,
            SimpleGridSchema,
            SimpleTableSchema,
            make_unique_all,
        )

        doc = self.to_structured(separator=separator)

        tables = []
        for src_table, table in zip(self.tables, doc.tables, strict=True):
            grids = []
            for grid in table.grids:
                rows = []
                for row in grid.rows:
                    keys = make_unique_all([list(e.key) for e in row.cells])
                    rows.append(
                        {
                            "_".join(map(str, k)): e.value
                            for k, e in zip(keys, row.cells, strict=True)
                        }
                    )
                grids.append(SimpleGridSchema(id=grid.id, rows=rows))

            tables.append(
                SimpleTableSchema(
                    id=table.id,
                    kv_items=src_table.view.kv_items_to_nested(separator=separator),
                    grids=grids,
                )
            )

        return SimpleDocumentSchema(
            document_name=self.document_name,
            tables=tables,
            paragraphs=[p.contents for p in doc.paragraphs],
        )

    def find_table_by_id(self, table_id: str) -> SemanticTable | None:
        """
        Search for a table by its ID.
        テーブルIDに対応するテーブルを返す

        Args:
            table_id (str): 検索するテーブルID
        """
        for table in self.tables:
            if table.id == str(table_id):
                return table

    def find_table_by_position(self, box: list[int]) -> SemanticTable | None:
        """
        Search for a table by its bounding box.
        テーブルの位置情報（bounding box）に対応するテーブルを返す

        Args:
            box (list[int]): 検索するバウンディングボックス [x1, y1, x2, y2]
        """
        from .tsp_semantics import overlap_ratio

        ratios = []
        for table in self.tables:
            ratios.append(overlap_ratio(box, table.box))

        if not ratios:
            return None

        max_idx = ratios.index(max(ratios))
        return self.tables[max_idx] if ratios[max_idx] > 0.5 else None

    def load_template_json(self, template_path: str) -> "TableSemanticParserResult":
        from .tsp_semantics import (
            TableSemanticParserTemplateSchema,
            apply_table_template,
        )

        with open(template_path, encoding="utf-8") as f:
            data = json.load(f)
        template = TableSemanticParserTemplateSchema.model_validate(data)
        return apply_table_template(self, template)

    def to_template(self, include_kv: bool = True, include_grids: bool = True):
        """Build a Pro-compatible editable template without mutating the result."""
        from .tsp_semantics import (
            CellTemplateSchema,
            TableSemanticContentsTemplateSchema,
            TableSemanticParserTemplateSchema,
            TemplateMetaSchema,
        )

        tables = []
        for table in self.tables:
            cells = {}
            entries = (
                table.cells.items()
                if isinstance(table.cells, dict)
                else enumerate(table.cells)
            )
            for cid, cell in entries:
                if cell.role == "group":
                    continue
                cells[cell.id or str(cid)] = CellTemplateSchema(
                    id=cell.id or (str(cid) if isinstance(table.cells, dict) else None),
                    box=list(cell.box),
                    role=cell.role,
                    contents=cell.contents,
                )
            tables.append(
                TableSemanticContentsTemplateSchema(
                    id=table.id,
                    style=table.style,
                    box=list(table.box),
                    cells=cells,
                    kv_items=[item.model_copy(deep=True) for item in table.kv_items]
                    if include_kv
                    else None,
                    grids=[grid.model_copy(deep=True) for grid in table.grids]
                    if include_grids
                    else None,
                )
            )
        # ID-less lists can only be matched by position.
        policy = (
            "bbox"
            if any(cell.id is None for table in tables for cell in table.cells.values())
            else "cell_id"
        )
        return TableSemanticParserTemplateSchema(
            meta=TemplateMetaSchema(match_policy=policy), tables=tables
        )

    def save_template_json(
        self, out_path: str, include_kv: bool = True, include_grids: bool = True
    ):
        template = self.to_template(include_kv, include_grids)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(
            template.model_dump_json(exclude_none=True, indent=2), encoding="utf-8"
        )

    def apply_template(self, template):
        """Apply a Pro template in place and return this page."""
        from .tsp_semantics import (
            TableSemanticParserTemplateSchema,
            apply_table_template,
        )

        template = TableSemanticParserTemplateSchema.model_validate(template)
        return apply_table_template(self, template)


class MultiPageTableSemanticParserResult(BaseModel):
    """Table semantic parsing result of a whole document"""

    pages: dict[int, TableSemanticParserResult] = Field(
        description="Dictionary of page index to TableSemanticParserResult",
    )

    def to_json(
        self,
        output_path: str,
        encoding: str = "utf-8",
        mode: str = "combine",
        page_index: list | None = None,
        output_mode: str = "raw",
        separator: str = "\n",
    ) -> list[dict]:
        """
        Save the result in JSON format

        Args:
            output_path: Path to save the JSON file
            encoding: File encoding
            mode: 'combine' to write a single file, 'separate' to write one file per page
            page_index: List of page indices to save
            output_mode: raw (Python API default), structured, simple, or template
            separator: Separator for values sharing the same key cells
        Returns:
            list[dict]: The saved pages
        """
        if output_mode not in {"raw", "structured", "simple", "template"}:
            raise ValueError(f"Unsupported TSP output mode: {output_mode}")
        if mode not in {"combine", "separate"}:
            raise ValueError(f"Unsupported split mode: {mode}")
        page_index = (
            list(self.pages)
            if page_index is None
            else make_page_index(page_index, len(self.pages))
        )

        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        results = []
        for idx in page_index:
            page = self.pages[idx]
            if output_mode == "raw":
                result = page.to_json()
            elif output_mode == "template":
                result = page.to_template().model_dump(exclude_none=True)
                result["num_page"] = idx
            else:
                view = (
                    page.to_structured(separator)
                    if output_mode == "structured"
                    else page.to_simple(separator)
                )
                result = {"num_page": idx, **view.model_dump()}
            results.append(result)

        export_results_to_file(
            results,
            output_path=output_path,
            mode=mode,
            encoding=encoding,
            page_index=page_index,
        )

        return results

    def to_structured(self, separator: str = "\n") -> dict:
        """Return page-indexed structured views."""
        return {idx: page.to_structured(separator) for idx, page in self.pages.items()}

    def to_simple(self, separator: str = "\n") -> dict:
        """Return page-indexed text-only views."""
        return {idx: page.to_simple(separator) for idx, page in self.pages.items()}

    def load_template_json(self, template_path: str):
        """Apply one Pro template to all pages or a list matched by num_page.

        Combined templates without num_page are matched by list position.
        Validation happens before any page is modified.
        """
        from .tsp_semantics import TableSemanticParserTemplateSchema

        with open(template_path, encoding="utf-8") as stream:
            data = json.load(stream)
        if isinstance(data, dict):
            template = TableSemanticParserTemplateSchema.model_validate(data)
            if "num_page" in data:
                templates = {int(data["num_page"]): template}
            else:
                templates = dict.fromkeys(self.pages, template)
        elif isinstance(data, list):
            templates = {}
            for index, item in enumerate(data):
                validated = TableSemanticParserTemplateSchema.model_validate(item)
                idx = int(item.get("num_page", index))
                if idx in templates:
                    raise ValueError(f"Duplicate template page: {idx}")
                templates[idx] = validated
        else:
            raise ValueError("Template must be a page object or a list of page objects")
        for idx, template in templates.items():
            if idx in self.pages:
                self.pages[idx].apply_template(template)
        return self

    def save_template_json(
        self, output_path: str, mode: str = "combine", page_index: list | None = None
    ):
        return self.to_json(
            output_path, mode=mode, page_index=page_index, output_mode="template"
        )
