"""Structured views and templates ported from YomiToku-Pro's TSP schema.

This module only operates on parsed results; no inference dependencies are needed.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, conlist

from .tsp_models import KvItem, LayoutElement, TableGrid

if TYPE_CHECKING:
    from .tsp_models import SemanticCell, SemanticTable, TableSemanticParserResult

MatchPolicy = Literal["cell_id", "bbox"]
UNKEYED_KEY = "_unkeyed"
NESTED_VALUE_KEY = "_value"


def overlap_ratio(box, candidate):
    """Fraction of candidate covered by box (the same matching rule as Pro)."""
    area = max(0, candidate[2] - candidate[0]) * max(0, candidate[3] - candidate[1])
    if not area:
        return 0.0
    width = max(0, min(box[2], candidate[2]) - max(box[0], candidate[0]))
    height = max(0, min(box[3], candidate[3]) - max(box[1], candidate[1]))
    return width * height / area


def make_unique_all(seq):
    counter = defaultdict(int)
    result = []

    for x in seq:
        key = tuple(x)
        idx = counter[key]
        result.append(x + [idx])
        counter[key] += 1

    for res, x in zip(result, seq, strict=False):
        if counter[tuple(x)] == 1:
            res.pop()

    return result


class TemplateMetaSchema(BaseModel):
    template_version: str = Field("beta", description="Template schema version")
    template_id: str | None = Field(None, description="Human-readable template id")
    notes: str | None = Field(None, description="Notes for template editors")

    match_policy: MatchPolicy = Field("cell_id", description="How to match cells")


class JsonView(BaseModel):
    """Serializable local view, with Pro-compatible JSON file export."""

    def to_json(self, out_path: str, encoding: str = "utf-8") -> dict:
        data = self.model_dump()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding=encoding
        )
        return data


class StructuredCellRefSchema(BaseModel):
    """構造化出力でテキストの由来セルを指す参照 (セルIDと座標)。"""

    id: str | None = Field(..., description="Cell id")
    box: conlist(int, min_length=4, max_length=4) = Field(
        ...,
        description="Bounding box of the cell in the format [x1, y1, x2, y2]",
    )


class StructuredEntrySchema(BaseModel):
    """key/value のテキストと、その由来セル参照を対で持つエントリ。

    key は外側 (親) ヘッダーから内側の順のテキスト配列で、key_cells と
    同じ順序で対応する。キーなしの単独セルでは空配列。
    kv_items では同一キーの複数 value が空間順に separator 結合され、
    value_cells に結合元セルが順序どおり並ぶ。grid の行セルでは
    value_cells は常に長さ1。
    """

    key: list[str] = Field(
        ...,
        description="Key texts from the outermost header to the innermost",
    )
    value: str = Field(..., description="Value text")
    key_cells: list[StructuredCellRefSchema] = Field(
        ...,
        description="Cells the key text originates from",
    )
    value_cells: list[StructuredCellRefSchema] = Field(
        ...,
        description="Cells the value text originates from",
    )


class StructuredGridRowSchema(BaseModel):
    cells: list[StructuredEntrySchema] = Field(
        ...,
        description="Entries in the row (column header as key, cell as value)",
    )


class StructuredGridSchema(BaseModel):
    id: str | None = Field(..., description="Unique identifier of the grid")
    box: conlist(int, min_length=4, max_length=4) = Field(
        ...,
        description="Bounding box of the grid in the format [x1, y1, x2, y2]",
    )
    n_row: int = Field(..., description="Number of rows in the table grid")
    n_col: int = Field(..., description="Number of columns in the table grid")
    rows: list[StructuredGridRowSchema] = Field(
        ...,
        description="Data rows (header rows are excluded)",
    )


class StructuredTableSchema(BaseModel):
    id: str | None = Field(None, description="Unique identifier of the table")
    box: conlist(int, min_length=4, max_length=4) = Field(
        ...,
        description="Bounding box of the table in the format [x1, y1, x2, y2]",
    )
    style: str = Field(
        ..., description="Border style of the table, e.g., ['border', 'borderless']"
    )
    kv_items: list[StructuredEntrySchema] = Field(
        ..., description="Resolved key-value items"
    )
    grids: list[StructuredGridSchema] = Field(
        ..., description="Resolved grid representations"
    )


class StructuredDocumentSchema(JsonView):
    """ドキュメント全体の構造化ビュー。

    TableSemanticParserResult (正規化スキーマ) からセルIDをテキストと座標に
    解決した非正規化形。ロスレスな往復が必要な場合は正規化スキーマを使う。
    """

    document_name: str | None = Field(
        None, description="Document name inferred from the first section heading"
    )
    tables: list[StructuredTableSchema] = Field(..., description="Structured tables")
    paragraphs: list[LayoutElement] = Field(
        ..., description="List of recognized paragraphs in the document"
    )


class SimpleGridSchema(BaseModel):
    id: str | None = Field(..., description="Unique identifier of the grid")
    rows: list[dict[str, str]] = Field(
        ...,
        description="Data rows as {column header: value} mappings",
    )


class SimpleTableSchema(BaseModel):
    id: str | None = Field(None, description="Unique identifier of the table")
    kv_items: dict[str, Any] = Field(
        ...,
        description=(
            "Resolved key-value items nested by header hierarchy. Values are "
            "strings, nested dicts (child headers), or lists (repeated "
            "same-text sibling headers)"
        ),
    )
    grids: list[SimpleGridSchema] = Field(..., description="Resolved grids")


class SimpleDocumentSchema(JsonView):
    """座標やセル参照などのメタ情報を持たない、テキストのみの構造化ビュー。"""

    document_name: str | None = Field(
        None, description="Document name inferred from the first section heading"
    )
    tables: list[SimpleTableSchema] = Field(..., description="Simple tables")
    paragraphs: list[str | None] = Field(
        ..., description="Paragraph texts in the document"
    )


class TableSemanticContentsView:
    def __init__(self, table: SemanticTable):
        self.table = table

    def kv_items_to_dict(self, separator="\n") -> dict:
        """
        Convert KV items into a hierarchical dict preserving key-cell nesting.
        KVアイテムを、キーセルの入れ子構造を保った階層dictに変換する。

        kv_items_to_nested のエイリアス。同一キーセル列の複数 value は
        空間順に separator で結合される。
        """
        return self.kv_items_to_nested(separator=separator)

    def grids_to_dict(self, ignore_space=True) -> list[dict]:
        """
        Convert table grids to a list of dictionaries.
        テーブルグリッドの内容を辞書形式に変換
        """

        t = self.table
        results = []
        for grid in t.grids:
            row_record_list = []
            for row in grid.data:
                parsed_row = {}

                cell_id_list = set()
                col_key_list, value_list = [], []

                for i, cell in enumerate(row):
                    if i >= len(grid.col_headers):
                        break
                    if cell is None:
                        continue
                    if cell in grid.col_headers[i]:
                        continue

                    ck = [t.safe_contents(i, ignore_space) for i in grid.col_headers[i]]
                    v = t.safe_contents(cell, ignore_space)

                    if cell in cell_id_list:
                        continue

                    col_key_list.append(ck)
                    value_list.append(v)
                    cell_id_list.add(cell)

                col_key_list = make_unique_all(col_key_list)
                for ck, v in zip(col_key_list, value_list, strict=False):
                    parsed_row["_".join(map(str, ck))] = v

                if parsed_row:
                    row_record_list.append(parsed_row)
            results.append({"id": grid.id, "rows": row_record_list})

        return results

    def _cell_refs(self, cell_ids) -> list[StructuredCellRefSchema]:
        """セルIDの列を StructuredCellRefSchema の列に解決する。

        cells に存在しないIDは黙って除外する (safe_contents が "" を返す
        挙動に合わせる)。
        """
        refs = []
        for cell_id in cell_ids:
            cell = self.table.find_cell_by_id(cell_id)
            if cell is None:
                continue
            refs.append(StructuredCellRefSchema(id=cell.id, box=cell.box))
        return refs

    def _kv_groups(self) -> list[dict]:
        """kv_items を同一キーセル列でグループ化し、value を空間順に整列する。

        統合の判定はキーの「テキスト」ではなくセルIDで行う。たまたま同じ
        ラベル文字列を持つ別のフィールド (別のキーセル) は統合しない。
        キーを持たない単独セルも統合せず、個別のグループのまま返す。
        複数 value は空間順 (縦横の広がりで軸を判定) に整列する。
        """
        t = self.table
        groups = []
        by_key = {}

        for kv in t.kv_items:
            # key は Union[str, List[str]]。bare str を文字単位で
            # イテレートしないよう正規化する。
            key_ids = [kv.key] if isinstance(kv.key, str) else list(kv.key)
            group_id = tuple(key_ids)

            # キーなしの単独セルはマージしない
            if key_ids and group_id in by_key:
                group = by_key[group_id]
            else:
                group = {"key_ids": list(key_ids), "values": []}
                groups.append(group)
                if key_ids:
                    by_key[group_id] = group

            group["values"].append(
                (t.safe_contents(kv.value), t.find_cell_by_id(kv.value), kv.value)
            )

        for group in groups:
            values = group["values"]
            if len(values) > 1:
                with_cell = [v for v in values if v[1] is not None]
                without_cell = [v for v in values if v[1] is None]
                if with_cell:
                    boxes = [v[1].box for v in with_cell]
                    x_spread = max(b[0] for b in boxes) - min(b[0] for b in boxes)
                    y_spread = max(b[1] for b in boxes) - min(b[1] for b in boxes)
                    axis = 1 if y_spread >= x_spread else 0
                    with_cell.sort(key=lambda v: v[1].box[axis])
                group["values"] = with_cell + without_cell

        return groups

    def kv_items_to_structured(self, separator="\n") -> list[StructuredEntrySchema]:
        """KVアイテムをテキスト+セル座標に解決したエントリ列に変換する。

        同一の「キーセル」(セルIDの並びが一致) を持つアイテムは1エントリに
        統合し、value を空間順に separator で結合する。value_cells には
        結合元セルが同じ順序で並ぶ。統合規則は _kv_groups を参照。
        """
        t = self.table
        entries = []
        for group in self._kv_groups():
            entries.append(
                StructuredEntrySchema(
                    key=[t.safe_contents(i) for i in group["key_ids"]],
                    value=separator.join(str(v[0]) for v in group["values"]),
                    key_cells=self._cell_refs(group["key_ids"]),
                    value_cells=self._cell_refs([v[2] for v in group["values"]]),
                )
            )

        return entries

    def kv_items_to_nested(self, separator="\n") -> dict:
        """KVアイテムを、キーセルの入れ子構造を保った階層dictに変換する。

        キーセルIDのチェーン (親ヘッダー → 子ヘッダー) から木を構築する。
        ノードの同一性はテキストではなくセルIDで判定し、同じ階層に同名
        テキストの別ノード (繰り返しブロック) が並ぶ場合は配列にする。
        親キーが値と子キーの両方を持つ場合、値は "_value" キーに入れる。
        キーなしの単独セルは予約キー UNKEYED_KEY ("_unkeyed") の下に並ぶ。
        同一キーセル列の複数 value の結合挙動は to_structured と同一。
        """
        t = self.table
        root = {"text": None, "children": {}, "order": [], "values": []}

        for i, group in enumerate(self._kv_groups()):
            if group["key_ids"]:
                chain = [(cid, t.safe_contents(cid)) for cid in group["key_ids"]]
            else:
                # キーなしは UNKEYED_KEY の葉として個別に扱う (結合しない)
                chain = [(f"__keyless_{i}", UNKEYED_KEY)]

            node = root
            for cell_id, text in chain:
                child = node["children"].get(cell_id)
                if child is None:
                    child = {
                        "text": text,
                        "children": {},
                        "order": [],
                        "values": [],
                    }
                    node["children"][cell_id] = child
                    node["order"].append(cell_id)
                node = child
            node["values"].append(separator.join(str(v[0]) for v in group["values"]))

        return self._render_nested_node(root)

    def _render_nested_node(self, node) -> dict:
        by_text = {}
        for cell_id in node["order"]:
            child = node["children"][cell_id]
            sub = self._render_nested_node(child)
            if child["values"]:
                # グループはキーセル列単位で一意なので values は高々1件
                sub = (
                    {NESTED_VALUE_KEY: child["values"][0], **sub}
                    if sub
                    else child["values"][0]
                )
            by_text.setdefault(child["text"], []).append(sub)

        return {
            text: items[0] if len(items) == 1 else items
            for text, items in by_text.items()
        }

    def grids_to_structured(self, ignore_space=True) -> list[StructuredGridSchema]:
        """グリッドをテキスト+セル座標に解決した行列構造に変換する。

        grids_to_dict と同じく、ヘッダ行のセル・行内で重複するセルID・
        空になった行は除外する。data の None 穴と col_headers より長い行は
        スキップする。
        """
        t = self.table
        results = []
        for grid in t.grids:
            rows = []
            for row in grid.data:
                entries = []
                seen_cell_ids = set()

                for i, cell_id in enumerate(row):
                    if i >= len(grid.col_headers):
                        break

                    if cell_id is None:
                        continue

                    if cell_id in grid.col_headers[i]:
                        continue

                    if cell_id in seen_cell_ids:
                        continue
                    seen_cell_ids.add(cell_id)

                    header_ids = list(grid.col_headers[i])
                    entries.append(
                        StructuredEntrySchema(
                            key=[t.safe_contents(h, ignore_space) for h in header_ids],
                            value=t.safe_contents(cell_id, ignore_space),
                            key_cells=self._cell_refs(header_ids),
                            value_cells=self._cell_refs([cell_id]),
                        )
                    )

                if entries:
                    rows.append(StructuredGridRowSchema(cells=entries))

            results.append(
                StructuredGridSchema(
                    id=grid.id,
                    box=grid.box,
                    n_row=grid.n_row,
                    n_col=grid.n_col,
                    rows=rows,
                )
            )

        return results


class CellTemplateSchema(BaseModel):
    # match に使う情報（どちらか入っていれば良い）
    id: str | None = Field(None, description="Cell id for matching")
    box: conlist(int, min_length=4, max_length=4) | None = Field(
        None, description="Cell bbox for matching"
    )

    # 上書き対象（差分でOK）
    role: str | None = Field(None, description="Role override")
    contents: str | None = Field(None, description="Contents override")


class TableSemanticContentsTemplateSchema(BaseModel):
    id: str | None = Field(
        None, description="Unique identifier of the table (optional)"
    )
    style: str | None = Field(None, description="Border style (optional)")

    # table matchingに使う（最小）
    box: conlist(int, min_length=4, max_length=4) = Field(
        ..., description="Bounding box [x1, y1, x2, y2]"
    )

    # テンプレ側は “差分” なので Dict[str, CellTemplateSchema] でOK
    # （キーはセルIDを想定。idが無いケースもあるので値側にも id を持たせてる）
    cells: dict[str, CellTemplateSchema] = Field(
        default_factory=dict,
        description="Template cells keyed by cell_id (or arbitrary key)",
    )

    # これらもテンプレで差し替えるなら optional にしておく
    kv_items: list[KvItem] | None = Field(
        None, description="Optional KV items override"
    )
    grids: list[TableGrid] | None = Field(None, description="Optional grids override")


class TableSemanticParserTemplateSchema(BaseModel):
    meta: TemplateMetaSchema = Field(
        ...,
        description="Metadata related to the table semantic parsing",
    )

    tables: list[TableSemanticContentsTemplateSchema] = Field(
        ...,
        description="List of tables with semantic information",
    )

    def find_table_by_id(
        self, table_id: str
    ) -> TableSemanticContentsTemplateSchema | None:
        """
        Search for a table by its ID.
        テーブルIDに対応するテーブルを返す

        Args:
            table_id (str): 検索するテーブルID
        """
        for table in self.tables:
            if table.id == str(table_id):
                return table


def _match_cell(
    table: SemanticTable,
    tcell: CellTemplateSchema,
    policy: str = "cell_id",
) -> SemanticCell | None:
    if policy == "cell_id":
        if not tcell.id:
            return None
        return table.find_cell_by_id(tcell.id)

    if policy == "bbox":
        if not tcell.box:
            return None
        candidates = table.search_cells_by_bbox(list(tcell.box))
        return candidates[0] if candidates else None

    return None


def apply_table_template(
    tables: TableSemanticParserResult,
    tmpl: TableSemanticParserTemplateSchema,
) -> TableSemanticParserResult:
    policy = getattr(tmpl.meta, "match_policy", "cell_id")

    for tmp_table in tmpl.tables:
        table = tables.find_table_by_position(tmp_table.box)
        if table is None:
            continue

        # cells: role/contents をテンプレ優先で上書き
        for cid, source_cell in tmp_table.cells.items():
            tcell = source_cell.model_copy(update={"id": source_cell.id or cid})
            cell = _match_cell(table, tcell, policy=policy)
            if cell is None:
                continue
            if tcell.role is not None:
                cell.role = tcell.role
            if tcell.contents is not None:
                cell.contents = tcell.contents

        # kv_items / grids: テンプレが持っているなら差し替え
        if tmp_table.kv_items is not None:
            table.kv_items = [item.model_copy(deep=True) for item in tmp_table.kv_items]
        if tmp_table.grids is not None:
            table.grids = [grid.model_copy(deep=True) for grid in tmp_table.grids]

    return tables
