"""Apply YomiToku Studio form-template JSON to TSP OCR words."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from functools import cmp_to_key
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .tsp_models import (
    KvItem,
    LayoutElement,
    SemanticCell,
    SemanticTable,
    TableGrid,
    TableSemanticParserResult,
)
from .utils import load_image, load_pdf


class _StudioModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class StudioTemplatePage(_StudioModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class StudioTemplateCell(_StudioModel):
    id: str
    norm_box: list[float] = Field(alias="normBox", min_length=4, max_length=4)
    role: str | None = None
    row: int | None = None
    col: int | None = None
    row_span: int | None = Field(None, alias="rowSpan")
    col_span: int | None = Field(None, alias="colSpan")
    meta: dict[str, Any] = Field(default_factory=dict)
    contents: str = ""

    @field_validator("norm_box")
    @classmethod
    def validate_box(cls, value):
        if not all(math.isfinite(n) for n in value):
            raise ValueError("normBox must contain finite numbers")
        if value[0] > value[2] or value[1] > value[3]:
            raise ValueError("normBox coordinates are reversed")
        return value


class StudioTemplateKvItem(_StudioModel):
    id: str | None = None
    key: list[str]
    value: str


class StudioTemplateGrid(_StudioModel):
    id: str | None = None
    norm_box: list[float] = Field(alias="normBox", min_length=4, max_length=4)
    n_row: int = Field(alias="nRow")
    n_col: int = Field(alias="nCol")
    col_headers: list[list[str]] = Field(alias="colHeaders")
    data: list[list[str | None]]


class StudioTemplateTable(_StudioModel):
    id: str
    norm_box: list[float] = Field(alias="normBox", min_length=4, max_length=4)
    style: str = "border"
    cells: list[StudioTemplateCell]
    kv_items: list[StudioTemplateKvItem] = Field(default_factory=list, alias="kvItems")
    grids: list[StudioTemplateGrid] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self):
        ids = [cell.id for cell in self.cells]
        if len(ids) != len(set(ids)):
            raise ValueError(f"table {self.id!r} contains duplicate cell ids")
        known = set(ids)
        refs = [ref for item in self.kv_items for ref in [*item.key, item.value]]
        refs.extend(
            ref
            for grid in self.grids
            for row in [*grid.col_headers, *grid.data]
            for ref in row
            if ref is not None
        )
        unknown = sorted(set(refs) - known)
        if unknown:
            raise ValueError(f"table {self.id!r} references unknown cells: {unknown}")
        return self


class StudioTemplateParagraph(_StudioModel):
    id: str
    norm_box: list[float] = Field(alias="normBox", min_length=4, max_length=4)
    role: str | None = None
    contents: str = ""


class StudioTemplateStructure(_StudioModel):
    tables: list[StudioTemplateTable] = Field(default_factory=list)
    paragraphs: list[StudioTemplateParagraph] = Field(default_factory=list)


class StudioFormTemplate(_StudioModel):
    kind: Literal["form-template"]
    version: Literal[2, 3]
    document_name: str | None = Field(None, alias="documentName")
    page: StudioTemplatePage
    structure: StudioTemplateStructure
    fields: list[dict[str, Any]]

    @model_validator(mode="after")
    def validate_structure(self):
        if not self.structure.tables and not self.structure.paragraphs:
            raise ValueError("template contains no layout structure")
        ids = [table.id for table in self.structure.tables]
        if len(ids) != len(set(ids)):
            raise ValueError("template contains duplicate table ids")
        return self


def load_studio_form_template(path: str | Path) -> StudioFormTemplate:
    with open(path, encoding="utf-8") as stream:
        return StudioFormTemplate.model_validate(json.load(stream))


def _denormalize(box: list[float], width: int, height: int) -> list[int]:
    return [
        round(box[0] * width),
        round(box[1] * height),
        round(box[2] * width),
        round(box[3] * height),
    ]


def _word_box(word) -> list[int]:
    xs = [point[0] for point in word.points]
    ys = [point[1] for point in word.points]
    return [min(xs), min(ys), max(xs), max(ys)]


def _overlap_ratio(box, candidate) -> float:
    area = max(0, candidate[2] - candidate[0]) * max(0, candidate[3] - candidate[1])
    if not area:
        return 0.0
    width = max(0, min(box[2], candidate[2]) - max(box[0], candidate[0]))
    height = max(0, min(box[3], candidate[3]) - max(box[1], candidate[1]))
    return width * height / area


def _compare_words(left, right) -> int:
    a, b = _word_box(left), _word_box(right)
    return a[1] - b[1] if abs(a[1] - b[1]) > 8 else a[0] - b[0]


def _ordered_text(words, separator="") -> str:
    return separator.join(
        word.content for word in sorted(words, key=cmp_to_key(_compare_words))
    ).strip()


def apply_studio_form_template(
    template: StudioFormTemplate,
    page: TableSemanticParserResult,
    width: int,
    height: int,
) -> TableSemanticParserResult:
    """Replace inferred structure with Studio structure and fill it from OCR words."""
    tables = []
    for source_table in template.structure.tables:
        cells = {
            source.id: SemanticCell(
                id=source.id,
                box=_denormalize(source.norm_box, width, height),
                role=source.role,
                contents="",
                row=source.row,
                col=source.col,
                row_span=source.row_span,
                col_span=source.col_span,
                meta={**source.meta, "fromTemplate": True},
            )
            for source in source_table.cells
        }
        assigned = defaultdict(list)
        for word in page.words:
            word_box = _word_box(word)
            candidates = [
                (_overlap_ratio(cell.box, word_box), cell_id)
                for cell_id, cell in cells.items()
                if cell.role != "group"
            ]
            if candidates:
                ratio, cell_id = max(candidates, key=lambda candidate: candidate[0])
                if ratio >= 0.2:
                    assigned[cell_id].append(word)

        source_cells = {cell.id: cell for cell in source_table.cells}
        for cell_id, cell in cells.items():
            text = _ordered_text(assigned[cell_id])
            source = source_cells[cell_id]
            cell.contents = (
                text
                if text
                else source.contents
                if cell.role in {"header", "group"}
                else ""
            )

        tables.append(
            SemanticTable(
                id=source_table.id,
                style=source_table.style,
                box=_denormalize(source_table.norm_box, width, height),
                cells=cells,
                kv_items=[
                    KvItem(id=item.id, key=item.key, value=item.value)
                    for item in source_table.kv_items
                ],
                grids=[
                    TableGrid(
                        id=grid.id,
                        box=_denormalize(grid.norm_box, width, height),
                        n_row=grid.n_row,
                        n_col=grid.n_col,
                        col_headers=grid.col_headers,
                        data=grid.data,
                    )
                    for grid in source_table.grids
                ],
            )
        )

    paragraphs = []
    for source in template.structure.paragraphs:
        box = _denormalize(source.norm_box, width, height)
        words = [
            word for word in page.words if _overlap_ratio(box, _word_box(word)) >= 0.5
        ]
        paragraphs.append(
            LayoutElement(
                id=source.id,
                box=box,
                score=1.0,
                role=source.role,
                contents=_ordered_text(words, separator="\n"),
            )
        )

    return page.model_copy(
        update={
            "document_name": template.document_name,
            "tables": tables,
            "paragraphs": paragraphs,
        }
    )


def apply_studio_template_to_document(
    document,
    template_path: str | Path,
    image_path: str | Path,
    dpi: int = 200,
):
    """Apply one Studio template to every selected page in a parsed TSP document."""
    template = load_studio_form_template(template_path)
    source = Path(image_path)
    images = (
        load_pdf(str(source), dpi=dpi)
        if source.suffix.lower() == ".pdf"
        else load_image(str(source))
    )
    for index, page in list(document.pages.items()):
        if index >= len(images):
            raise ValueError(f"Source document has no page {index}")
        height, width = images[index].shape[:2]
        document.pages[index] = apply_studio_form_template(
            template, page, width=width, height=height
        )
    return document
