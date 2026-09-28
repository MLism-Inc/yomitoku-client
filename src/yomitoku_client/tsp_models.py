"""
Data models for the YomiToku-Pro Table Semantic Parser (TSP) API.

The TSP endpoint (``YOMITOKU_SAGEMAKER_APP=table_semantic_parser``) returns the
semantic structure of every table in a page:

* ``cells``     : detected cells as a list or keyed by cell id (contents / role / span)
* ``kv_items``  : key-value pairs resolved from form-style layouts
* ``grids``     : row/column grids with their column headers

These models mirror the API response so it can be validated and saved as JSON.
Interpreting the structure (resolving cell ids to texts, rendering, visualizing)
is out of scope here.

The response envelope is the same as the document analyzer
(``{"result": [<page>, ...]}``), so :class:`~yomitoku_client.client.YomitokuClient`
can be used unchanged; only the parsing side differs.
"""

import os
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
    ) -> list[dict]:
        """
        Save the result in JSON format

        Args:
            output_path: Path to save the JSON file
            encoding: File encoding
            mode: 'combine' to write a single file, 'separate' to write one file per page
            page_index: List of page indices to save
        Returns:
            list[dict]: The saved pages
        """
        page_index = make_page_index(page_index, len(self.pages))

        base_dir = os.path.dirname(output_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)

        results = [self.pages[idx].to_json() for idx in page_index]

        export_results_to_file(
            results,
            output_path=output_path,
            mode=mode,
            encoding=encoding,
            page_index=page_index,
        )

        return results
