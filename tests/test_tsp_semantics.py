"""Regression cases ported from Pro to keep structured/simple output compatible."""

import json

from yomitoku_client.tsp_models import KvItem, SemanticCell, SemanticTable, TableGrid


def mk_cell(
    cid: str, box, role="cell", contents="", row=0, col=0, row_span=1, col_span=1
):
    return SemanticCell(
        id=cid,
        box=list(box),
        role=role,
        contents=contents,
        row=row,
        col=col,
        row_span=row_span,
        col_span=col_span,
        meta={},
    )


def mk_grid(grid_id: str, box, data, col_headers):
    return TableGrid(
        id=grid_id,
        box=list(box),
        n_row=len(data),
        n_col=len(data[0]) if data else 0,
        data=data,
        col_headers=col_headers,
    )


def mk_table(
    *,
    table_id="t0",
    style="border",
    box=(0, 0, 300, 200),
    cells=None,
    kv_items=None,
    grids=None,
):
    return SemanticTable(
        id=table_id,
        style=style,
        box=list(box),
        cells=cells or {},
        kv_items=kv_items or [],
        grids=grids or [],
    )


def test_view_kv_items_to_structured_attaches_cells():
    cells = {
        "k": mk_cell("k", (0, 0, 100, 30), role="header", contents="名前"),
        "v": mk_cell("v", (100, 0, 300, 30), role="cell", contents="太郎"),
    }
    kv_items = [KvItem(id="kv0", key=["k"], value="v")]
    t = mk_table(cells=cells, kv_items=kv_items)

    entries = t.view.kv_items_to_structured()

    assert len(entries) == 1
    e = entries[0]
    assert e.key == ["名前"]
    assert e.value == "太郎"
    assert [c.id for c in e.key_cells] == ["k"]
    assert [list(c.box) for c in e.key_cells] == [[0, 0, 100, 30]]
    assert [c.id for c in e.value_cells] == ["v"]
    assert [list(c.box) for c in e.value_cells] == [[100, 0, 300, 30]]


def test_view_kv_items_to_structured_merges_same_key_cell_vertically():
    """同一キーセルの複数valueは空間順に結合され、value_cellsが順序を保持する"""
    cells = {
        "k": mk_cell("k", (0, 0, 100, 60), role="header", contents="住所"),
        "v1": mk_cell("v1", (100, 0, 300, 30), role="cell", contents="東京都"),
        "v2": mk_cell("v2", (100, 30, 300, 60), role="cell", contents="新宿区"),
    }
    kv_items = [
        KvItem(id=None, key=["k"], value="v2"),  # 意図的に逆順
        KvItem(id=None, key=["k"], value="v1"),
    ]
    t = mk_table(cells=cells, kv_items=kv_items)

    entries = t.view.kv_items_to_structured()

    assert len(entries) == 1
    e = entries[0]
    assert e.key == ["住所"]
    assert e.value == "東京都\n新宿区"  # y座標でソートされる
    assert [c.id for c in e.value_cells] == ["v1", "v2"]
    assert [c.id for c in e.key_cells] == ["k"]


def test_view_kv_items_to_structured_keeps_same_text_different_cells_separate():
    """同じラベル文字列でも別のキーセルなら統合しない"""
    cells = {
        "k1": mk_cell("k1", (0, 0, 100, 30), role="header", contents="住所"),
        "k2": mk_cell("k2", (0, 200, 100, 230), role="header", contents="住所"),
        "v1": mk_cell("v1", (100, 0, 300, 30), role="cell", contents="東京都"),
        "v2": mk_cell("v2", (100, 200, 300, 230), role="cell", contents="大阪府"),
    }
    kv_items = [
        KvItem(id=None, key=["k1"], value="v1"),
        KvItem(id=None, key=["k2"], value="v2"),
    ]
    t = mk_table(cells=cells, kv_items=kv_items)

    entries = t.view.kv_items_to_structured()

    assert len(entries) == 2
    assert [(e.key, e.value) for e in entries] == [
        (["住所"], "東京都"),
        (["住所"], "大阪府"),
    ]
    assert [c.id for c in entries[0].key_cells] == ["k1"]
    assert [c.id for c in entries[1].key_cells] == ["k2"]


def test_view_kv_items_to_structured_normalizes_bare_str_key():
    """key が bare str でも文字単位に分解されない"""
    cells = {
        "k": mk_cell("k", (0, 0, 100, 30), role="header", contents="名前"),
        "v": mk_cell("v", (100, 0, 300, 30), role="cell", contents="太郎"),
    }
    kv_items = [KvItem(id=None, key="k", value="v")]
    t = mk_table(cells=cells, kv_items=kv_items)

    entries = t.view.kv_items_to_structured()

    assert len(entries) == 1
    assert entries[0].key == ["名前"]
    assert [c.id for c in entries[0].key_cells] == ["k"]


def test_view_kv_items_to_structured_skips_missing_cells():
    """cells に存在しないIDはテキスト空・セル参照なしで安全に処理される"""
    cells = {
        "k": mk_cell("k", (0, 0, 100, 30), role="header", contents="名前"),
    }
    kv_items = [KvItem(id=None, key=["k"], value="missing")]
    t = mk_table(cells=cells, kv_items=kv_items)

    entries = t.view.kv_items_to_structured()

    assert len(entries) == 1
    assert entries[0].value == ""
    assert entries[0].value_cells == []


def test_view_grids_to_structured_resolves_headers_and_cells():
    cells = {
        "h1": mk_cell("h1", (0, 0, 10, 10), role="header", contents="項目"),
        "h2": mk_cell("h2", (10, 0, 20, 10), role="header", contents="値"),
        "a": mk_cell("a", (0, 10, 10, 20), role="cell", contents="AA"),
        "b": mk_cell("b", (10, 10, 20, 20), role="cell", contents="BB"),
    }
    grid = mk_grid(
        "g0",
        (0, 0, 20, 20),
        data=[["h1", "h2"], ["a", "b"]],
        col_headers=[["h1"], ["h2"]],
    )
    t = mk_table(cells=cells, grids=[grid])

    out = t.view.grids_to_structured()

    assert len(out) == 1
    g = out[0]
    assert g.id == "g0"
    assert g.n_row == 2 and g.n_col == 2
    # ヘッダ行は除外され、データ行のみ
    assert len(g.rows) == 1
    row = g.rows[0].cells
    assert [(e.key, e.value) for e in row] == [(["項目"], "AA"), (["値"], "BB")]
    assert [c.id for c in row[0].key_cells] == ["h1"]
    assert [c.id for c in row[0].value_cells] == ["a"]
    assert [list(c.box) for c in row[0].value_cells] == [[0, 10, 10, 20]]


def test_view_grids_to_structured_handles_none_holes_and_long_rows():
    """data の None 穴はスキップ、col_headers より長い行は安全に打ち切る"""
    cells = {
        "h1": mk_cell("h1", (0, 0, 10, 10), role="header", contents="A"),
        "a": mk_cell("a", (0, 10, 10, 20), role="cell", contents="X"),
        "b": mk_cell("b", (10, 10, 20, 20), role="cell", contents="Y"),
    }
    grid = mk_grid(
        "g0",
        (0, 0, 20, 20),
        data=[[None, "a", "b"]],  # col_headers は1列分のみ
        col_headers=[["h1"]],
    )
    t = mk_table(cells=cells, grids=[grid])

    out = t.view.grids_to_structured()

    # None はスキップ、範囲外の "a"(idx1)/"b"(idx2) は打ち切りで空行 -> rows なし
    assert out[0].rows == []


def test_to_structured_builds_document_with_paragraphs():
    from yomitoku_client.tsp_models import (
        LayoutElement as Element,
        TableSemanticParserResult,
    )

    cells = {
        "k": mk_cell("k", (0, 0, 100, 30), role="header", contents="名前"),
        "v": mk_cell("v", (100, 0, 300, 30), role="cell", contents="太郎"),
    }
    kv_items = [KvItem(id="kv0", key=["k"], value="v")]
    table = mk_table(cells=cells, kv_items=kv_items)
    paragraph = Element(
        id="p0", box=[0, 100, 200, 130], score=0.9, role=None, contents="本文"
    )
    doc = TableSemanticParserResult(
        document_name="申請書", tables=[table], paragraphs=[paragraph], words=[]
    )

    structured = doc.to_structured()

    assert len(structured.tables) == 1
    assert structured.tables[0].id == "t0"
    assert structured.tables[0].kv_items[0].key == ["名前"]
    assert structured.document_name == "申請書"
    assert len(structured.paragraphs) == 1
    assert structured.paragraphs[0].contents == "本文"

    # BaseSchema 経由で JSON シリアライズ可能
    dumped = structured.model_dump()
    assert dumped["tables"][0]["kv_items"][0]["value_cells"][0]["id"] == "v"


def test_to_simple_drops_metadata_and_keeps_texts():
    from yomitoku_client.tsp_models import (
        LayoutElement as Element,
        TableSemanticParserResult,
    )

    cells = {
        "k": mk_cell("k", (0, 0, 100, 60), role="header", contents="住所"),
        "k2": mk_cell("k2", (0, 200, 100, 230), role="header", contents="住所"),
        "v1": mk_cell("v1", (100, 0, 300, 30), role="cell", contents="東京都"),
        "v2": mk_cell("v2", (100, 30, 300, 60), role="cell", contents="新宿区"),
        "v3": mk_cell("v3", (100, 200, 300, 230), role="cell", contents="大阪府"),
        "h1": mk_cell("h1", (0, 100, 10, 110), role="header", contents="項目"),
        "h2": mk_cell("h2", (10, 100, 20, 110), role="header", contents="値"),
        "a": mk_cell("a", (0, 110, 10, 120), role="cell", contents="AA"),
        "b": mk_cell("b", (10, 110, 20, 120), role="cell", contents="BB"),
    }
    kv_items = [
        # 同一キーセル k に2つの値 -> 結合される
        KvItem(id=None, key=["k"], value="v1"),
        KvItem(id=None, key=["k"], value="v2"),
        # 同名テキストだが別セル k2 -> 結合されず _0/_1 で区別される
        KvItem(id=None, key=["k2"], value="v3"),
    ]
    grid = mk_grid(
        "g0",
        (0, 100, 20, 120),
        data=[["h1", "h2"], ["a", "b"]],
        col_headers=[["h1"], ["h2"]],
    )
    table = mk_table(cells=cells, kv_items=kv_items, grids=[grid])
    paragraph = Element(
        id="p0", box=[0, 200, 200, 230], score=0.9, role=None, contents="本文"
    )
    doc = TableSemanticParserResult(
        document_name="申請書", tables=[table], paragraphs=[paragraph], words=[]
    )

    simple = doc.to_simple()

    assert len(simple.tables) == 1
    assert simple.document_name == "申請書"
    t = simple.tables[0]
    # 同一キーセルは結合、同名別セルは配列で区別される
    assert t.kv_items == {"住所": ["東京都\n新宿区", "大阪府"]}
    assert t.grids[0].id == "g0"
    assert t.grids[0].rows == [{"項目": "AA", "値": "BB"}]
    assert simple.paragraphs == ["本文"]

    # 座標・セル参照が一切含まれない
    dumped = simple.model_dump()
    assert "box" not in json.dumps(dumped, ensure_ascii=False)


def test_to_simple_suffixes_duplicate_headers_in_grid_row():
    from yomitoku_client.tsp_models import TableSemanticParserResult

    cells = {
        "h1": mk_cell("h1", (0, 0, 10, 10), role="header", contents="日付"),
        "h2": mk_cell("h2", (10, 0, 20, 10), role="header", contents="日付"),
        "a": mk_cell("a", (0, 10, 10, 20), role="cell", contents="1月"),
        "b": mk_cell("b", (10, 10, 20, 20), role="cell", contents="2月"),
    }
    grid = mk_grid(
        "g0",
        (0, 0, 20, 20),
        data=[["a", "b"]],
        col_headers=[["h1"], ["h2"]],
    )
    table = mk_table(cells=cells, grids=[grid])
    doc = TableSemanticParserResult(tables=[table], paragraphs=[], words=[])

    simple = doc.to_simple()

    # 行内でヘッダテキストが重複する場合は _0/_1 で区別され、値が失われない
    assert simple.tables[0].grids[0].rows == [{"日付_0": "1月", "日付_1": "2月"}]


def test_view_kv_items_to_structured_does_not_merge_keyless_cells():
    """キーなしの単独セルは同一(空)キーでも結合されない"""
    cells = {
        "v1": mk_cell("v1", (0, 0, 100, 30), role="cell", contents="I_SUPER流通系"),
        "v2": mk_cell("v2", (0, 30, 100, 60), role="cell", contents="請求"),
    }
    kv_items = [
        KvItem(id=None, key=[], value="v1"),
        KvItem(id=None, key=[], value="v2"),
    ]
    t = mk_table(cells=cells, kv_items=kv_items)

    entries = t.view.kv_items_to_structured()

    assert len(entries) == 2
    assert [(e.key, e.value) for e in entries] == [
        ([], "I_SUPER流通系"),
        ([], "請求"),
    ]
    assert [c.id for c in entries[0].value_cells] == ["v1"]
    assert [c.id for c in entries[1].value_cells] == ["v2"]


def test_to_simple_keeps_keyless_cells_separate_as_list():
    """--simple でもキーなしセルは結合されず、_unkeyed の下に配列で並ぶ"""
    from yomitoku_client.tsp_models import TableSemanticParserResult

    cells = {
        "v1": mk_cell("v1", (0, 0, 100, 30), role="cell", contents="A"),
        "v2": mk_cell("v2", (0, 30, 100, 60), role="cell", contents="B"),
    }
    kv_items = [
        KvItem(id=None, key=[], value="v1"),
        KvItem(id=None, key=[], value="v2"),
    ]
    table = mk_table(cells=cells, kv_items=kv_items)
    doc = TableSemanticParserResult(tables=[table], paragraphs=[], words=[])

    simple = doc.to_simple()

    assert simple.tables[0].kv_items == {"_unkeyed": ["A", "B"]}


def test_view_kv_items_to_nested_groups_by_parent_header():
    """入れ子ヘッダーは親ヘッダーでグループ化された階層dictになる"""
    cells = {
        "p": mk_cell("p", (0, 0, 20, 60), role="header", contents="申込者情報"),
        "k1": mk_cell("k1", (20, 0, 60, 30), role="header", contents="団体名"),
        "k2": mk_cell("k2", (20, 30, 60, 60), role="header", contents="電話番号"),
        "v1": mk_cell("v1", (60, 0, 200, 30), role="cell", contents="MLism"),
        "v2": mk_cell("v2", (60, 30, 200, 60), role="cell", contents="090"),
        "s": mk_cell("s", (0, 60, 60, 90), role="header", contents="備考"),
        "sv": mk_cell("sv", (60, 60, 200, 90), role="cell", contents="なし"),
    }
    kv_items = [
        KvItem(id=None, key=["p", "k1"], value="v1"),
        KvItem(id=None, key=["p", "k2"], value="v2"),
        KvItem(id=None, key=["s"], value="sv"),
    ]
    t = mk_table(cells=cells, kv_items=kv_items)

    nested = t.view.kv_items_to_nested()

    assert nested == {
        "申込者情報": {"団体名": "MLism", "電話番号": "090"},
        "備考": "なし",
    }


def test_view_kv_items_to_nested_repeated_blocks_become_list():
    """同名テキストの別親ヘッダー (繰り返しブロック) は配列になる"""
    cells = {
        "p1": mk_cell("p1", (0, 0, 20, 60), role="header", contents="扶養親族"),
        "p2": mk_cell("p2", (0, 60, 20, 120), role="header", contents="扶養親族"),
        "n1": mk_cell("n1", (20, 0, 60, 30), role="header", contents="氏名"),
        "n2": mk_cell("n2", (20, 60, 60, 90), role="header", contents="氏名"),
        "v1": mk_cell("v1", (60, 0, 200, 30), role="cell", contents="山田太郎"),
        "v2": mk_cell("v2", (60, 60, 200, 90), role="cell", contents="山田花子"),
    }
    kv_items = [
        KvItem(id=None, key=["p1", "n1"], value="v1"),
        KvItem(id=None, key=["p2", "n2"], value="v2"),
    ]
    t = mk_table(cells=cells, kv_items=kv_items)

    nested = t.view.kv_items_to_nested()

    assert nested == {
        "扶養親族": [{"氏名": "山田太郎"}, {"氏名": "山田花子"}],
    }


def test_view_kv_items_to_nested_parent_with_value_and_children():
    """親キーが値と子キーの両方を持つ場合、値は _value に入る"""
    cells = {
        "p": mk_cell("p", (0, 0, 20, 60), role="header", contents="扶養親族"),
        "pv": mk_cell("pv", (20, 0, 60, 30), role="cell", contents="有"),
        "n": mk_cell("n", (20, 30, 60, 60), role="header", contents="氏名"),
        "nv": mk_cell("nv", (60, 30, 200, 60), role="cell", contents="山田太郎"),
    }
    kv_items = [
        KvItem(id=None, key=["p"], value="pv"),
        KvItem(id=None, key=["p", "n"], value="nv"),
    ]
    t = mk_table(cells=cells, kv_items=kv_items)

    nested = t.view.kv_items_to_nested()

    assert nested == {
        "扶養親族": {"_value": "有", "氏名": "山田太郎"},
    }


def test_view_kv_items_to_nested_merges_values_on_same_key_chain():
    """同一キーセル列の複数 value は to_structured と同様に separator 結合"""
    cells = {
        "p": mk_cell("p", (0, 0, 20, 60), role="header", contents="住所"),
        "v1": mk_cell("v1", (20, 0, 200, 30), role="cell", contents="東京都"),
        "v2": mk_cell("v2", (20, 30, 200, 60), role="cell", contents="新宿区"),
    }
    kv_items = [
        KvItem(id=None, key=["p"], value="v1"),
        KvItem(id=None, key=["p"], value="v2"),
    ]
    t = mk_table(cells=cells, kv_items=kv_items)

    nested = t.view.kv_items_to_nested(separator="-")

    assert nested == {"住所": "東京都-新宿区"}
