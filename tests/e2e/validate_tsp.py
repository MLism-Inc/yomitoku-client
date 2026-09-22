#!/usr/bin/env python3
"""
Table Semantic Parser の出力を検証する。

チェック内容:

  ERROR (必ず満たすべき構造)
    - API のスキーマに適合する（--schema 指定時。OpenAPI 定義で検証する）
    - エンドポイントの生レスポンスと、client のモデルを通した結果が一致する
      （= client がフィールドを取りこぼしていない。--raw 指定時）
    - yomitoku-client の pydantic モデルでパースできる（= スキーマ適合）
    - kv_items / grids が参照する cell_id が cells に存在する
    - box が [x1, y1, x2, y2] で x1 < x2, y1 < y2（画像サイズが分かる場合は範囲内）
    - words.points が 4 点である
    - num_page が昇順で重複しない（想定ページを渡した場合は完全一致）

  WARN (壊れてはいないが確認したい差異)
    - grid の n_row / n_col と data の実形状が一致しない
    - col_headers の数と n_col が一致しない
    - スコアが 0〜1 の範囲外

認識されたテキストの内容は検証しない（モデル更新で変化するため）。

    python tests/e2e/validate_tsp.py results/table_jpg.json --input results/inputs/table.jpg
"""

import argparse
import json
import re
import sys
from pathlib import Path

from yomitoku_client import parse_table_semantic_parser
from yomitoku_client.exceptions import DocumentAnalysisError


class Findings:
    """検証結果（エラーと警告）を集める"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def load_pages(path: Path) -> list[dict]:
    """CLI 出力・生レスポンスのどちらの形でもページ配列にそろえる"""
    data = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(data, dict) and "result" in data:
        # エンドポイントの生レスポンス
        return list(data["result"])
    if isinstance(data, list):
        # yomitoku-client の JSON 出力（combine）
        return data
    if isinstance(data, dict):
        # yomitoku-client の JSON 出力（separate: 1 ページ）
        return [data]

    raise ValueError(f"Unsupported JSON structure: {path}")


def image_size(path: Path | None) -> tuple[int, int] | None:
    """box の範囲チェック用に画像サイズを返す（PDF は対象外）"""
    if path is None or path.suffix.lower() == ".pdf":
        return None

    try:
        from PIL import Image

        with Image.open(path) as img:
            return img.size
    except Exception:
        return None


def check_box(box, where: str, size, findings: Findings) -> None:
    if not isinstance(box, list) or len(box) != 4:
        findings.error(f"{where}: box の要素数が 4 ではない ({box})")
        return

    x1, y1, x2, y2 = box
    if x1 >= x2 or y1 >= y2:
        findings.error(f"{where}: box の座標が不正 ({box})")
        return

    if size is not None:
        width, height = size
        # 端で 1px はみ出す程度は許容する
        if x1 < -1 or y1 < -1 or x2 > width + 1 or y2 > height + 1:
            findings.warn(f"{where}: box が画像範囲外 ({box}, image={width}x{height})")


def check_table(table, page_no: int, size, findings: Findings) -> dict:
    """1 つの表の参照整合性と形状を検証する"""
    where = f"page {page_no} table {table.id}"
    check_box(table.box, where, size, findings)

    cell_ids = set(table.cells)
    for cell_id, cell in table.cells.items():
        check_box(cell.box, f"{where} cell {cell_id}", size, findings)
        if cell.id is not None and cell.id != cell_id:
            findings.warn(
                f"{where} cell {cell_id}: cells のキーと cell.id が一致しない ({cell.id})"
            )

    for kv_item in table.kv_items:
        key_ids = [kv_item.key] if isinstance(kv_item.key, str) else list(kv_item.key)
        for key_id in key_ids:
            if key_id not in cell_ids:
                findings.error(
                    f"{where} kv_item {kv_item.id}: key が参照する cell_id が無い ({key_id})"
                )
        if kv_item.value not in cell_ids:
            findings.error(
                f"{where} kv_item {kv_item.id}: value が参照する cell_id が無い ({kv_item.value})"
            )

    for grid in table.grids:
        grid_where = f"{where} grid {grid.id}"
        check_box(grid.box, grid_where, size, findings)

        if len(grid.data) != grid.n_row:
            findings.warn(
                f"{grid_where}: n_row={grid.n_row} だが data の行数は {len(grid.data)}"
            )
        if len(grid.col_headers) != grid.n_col:
            findings.warn(
                f"{grid_where}: n_col={grid.n_col} だが col_headers は {len(grid.col_headers)} 列"
            )

        for row_index, row in enumerate(grid.data):
            if len(row) != grid.n_col:
                findings.warn(
                    f"{grid_where} row {row_index}: n_col={grid.n_col} だが {len(row)} 列"
                )
            for cell_id in row:
                if cell_id is not None and cell_id not in cell_ids:
                    findings.error(
                        f"{grid_where} row {row_index}: data の cell_id が無い ({cell_id})"
                    )

        for col_index, header in enumerate(grid.col_headers):
            for cell_id in header:
                if cell_id not in cell_ids:
                    findings.error(
                        f"{grid_where} col {col_index}: col_headers の cell_id が無い ({cell_id})"
                    )

    return {
        "id": table.id,
        "style": table.style,
        "cells": len(table.cells),
        "kv_items": len(table.kv_items),
        "grids": len(table.grids),
    }


def check_page(page, size, findings: Findings) -> dict:
    """1 ページ分の段落・単語・表を検証する"""
    for index, paragraph in enumerate(page.paragraphs):
        check_box(
            paragraph.box, f"page {page.num_page} paragraph {index}", size, findings
        )

    for index, word in enumerate(page.words):
        where = f"page {page.num_page} word {index}"
        if len(word.points) != 4:
            findings.error(f"{where}: points が 4 点ではない ({len(word.points)})")
        for score_name in ("det_score", "rec_score"):
            score = getattr(word, score_name)
            if not 0.0 <= score <= 1.0:
                findings.warn(f"{where}: {score_name} が 0〜1 の範囲外 ({score})")

    tables = [
        check_table(table, page.num_page, size, findings) for table in page.tables
    ]

    return {
        "num_page": page.num_page,
        "tables": tables,
        "n_tables": len(page.tables),
        "n_paragraphs": len(page.paragraphs),
        "n_words": len(page.words),
    }


# client が独自に補うキー（差分として報告しない）
CLIENT_ADDED_KEYS = ("num_page",)


def normalize_path(path: str) -> str:
    """同種の差分を 1 件に集約するためのキーを作る

    配列の添字と ID 形式のキー（c0 / t0 / g0 / kv0 など）をまとめるので、
    「全セルで同じフィールドが欠けている」ようなケースが 1 行に集約される。
    """
    path = re.sub(r"\[\d+\]", "[]", path)
    return re.sub(r"\.[A-Za-z]+\d+(?=\.|$)", ".*", path)


def diff_structures(raw, dumped, path: str, seen: set, findings: Findings) -> None:
    """生レスポンスと client のモデルを通した結果を突き合わせる

    pydantic は既定で未知フィールドを捨てるため、「pro が返しているのに client が
    持っていないフィールド」はこの差分でしか見つからない。
    """

    def report(kind: str, message: str) -> None:
        key = (kind, normalize_path(message.split(":")[0]))
        if key in seen:
            return
        seen.add(key)
        (findings.error if kind == "error" else findings.warn)(message)

    if isinstance(raw, dict) and isinstance(dumped, dict):
        for key, value in raw.items():
            if key not in dumped:
                report(
                    "error", f"{path}.{key}: レスポンスにあるが client のモデルに無い"
                )
                continue
            diff_structures(value, dumped[key], f"{path}.{key}", seen, findings)
        for key in dumped:
            if key not in raw and key not in CLIENT_ADDED_KEYS:
                report("warn", f"{path}.{key}: client が既定値で補っている")
        return

    if isinstance(raw, list) and isinstance(dumped, list):
        if len(raw) != len(dumped):
            report(
                "error",
                f"{path}: 要素数が違う (response={len(raw)}, model={len(dumped)})",
            )
            return
        for index, (raw_item, dumped_item) in enumerate(zip(raw, dumped, strict=False)):
            diff_structures(raw_item, dumped_item, f"{path}[{index}]", seen, findings)
        return

    if raw != dumped:
        report("warn", f"{path}: 値が一致しない (response={raw!r}, model={dumped!r})")


def check_roundtrip(
    raw_pages: list[dict], pages: list[dict], findings: Findings
) -> None:
    """生レスポンスと client の出力をページ単位で突き合わせる"""
    if len(raw_pages) != len(pages):
        findings.error(
            f"生レスポンスと出力でページ数が違う (raw={len(raw_pages)}, output={len(pages)})"
        )
        return

    seen: set = set()
    for index, (raw_page, page) in enumerate(zip(raw_pages, pages, strict=False)):
        diff_structures(raw_page, page, f"page[{index}]", seen, findings)


def load_schema_document(schema_path: Path) -> dict:
    """スキーマを読み込む（OpenAPI の YAML / JSON、または JSON Schema）"""
    text = schema_path.read_text(encoding="utf-8")
    if schema_path.suffix.lower() in (".yaml", ".yml"):
        import yaml

        return yaml.safe_load(text)
    return json.loads(text)


def validate_with_schema(
    pages: list[dict], schema_path: Path, findings: Findings
) -> None:
    """API のスキーマ定義で検証する

    OpenAPI を渡した場合は components.schemas.TSPResponse を使う。プレーンな
    JSON Schema を渡した場合はそれをそのまま使う。
    client が付与する num_page は API のスキーマには無い（additionalProperties:
    false）ので、検証前に取り除く。
    """
    try:
        import jsonschema
    except ImportError:
        findings.warn("jsonschema が未インストールのため --schema の検証をスキップした")
        return

    try:
        document = load_schema_document(schema_path)
    except ImportError:
        findings.warn("PyYAML が未インストールのため --schema の検証をスキップした")
        return

    components = document.get("components", {}).get("schemas", {})
    if "TSPResponse" in components:
        schema = {"$ref": "#/components/schemas/TSPResponse", **document}
    else:
        schema = document

    payload = {
        "result": [
            {key: value for key, value in page.items() if key not in CLIENT_ADDED_KEYS}
            for page in pages
        ]
    }

    try:
        jsonschema.validate(payload, schema)
    except jsonschema.ValidationError as e:
        findings.error(f"スキーマ検証に失敗: {e.message} (at {list(e.absolute_path)})")


def validate(
    path: Path,
    input_path: Path | None = None,
    schema_path: Path | None = None,
    expect_pages: int | None = None,
    expect_page_numbers: list[int] | None = None,
    raw_path: Path | None = None,
) -> dict:
    """1 ファイル分の検証を行い、結果サマリを返す"""
    findings = Findings()
    pages = load_pages(path)

    if expect_pages is not None and len(pages) != expect_pages:
        findings.error(
            f"ページ数が想定と違う (expected={expect_pages}, actual={len(pages)})"
        )

    summary: dict = {
        "file": str(path),
        "n_pages": len(pages),
        "pages": [],
    }

    try:
        document = parse_table_semantic_parser({"result": pages})
    except DocumentAnalysisError as e:
        findings.error(f"pydantic モデルでパースできない: {e}")
        return _finish(summary, findings)

    # --pages でページを絞った場合は元の番号が残るため、想定を渡せるようにする
    page_numbers = sorted(document.pages)
    if expect_page_numbers is not None:
        if page_numbers != expect_page_numbers:
            findings.error(
                f"num_page が想定と違う (expected={expect_page_numbers}, actual={page_numbers})"
            )
    elif expect_pages is not None:
        if page_numbers != list(range(expect_pages)):
            findings.error(f"num_page が 0 からの連番になっていない ({page_numbers})")
    elif page_numbers != sorted(set(page_numbers)):
        findings.error(f"num_page が昇順・一意になっていない ({page_numbers})")

    size = image_size(input_path)
    for num_page in page_numbers:
        summary["pages"].append(check_page(document.pages[num_page], size, findings))

    if raw_path is not None:
        check_roundtrip(load_pages(raw_path), pages, findings)

    if schema_path is not None:
        validate_with_schema(pages, schema_path, findings)

    return _finish(summary, findings)


def _finish(summary: dict, findings: Findings) -> dict:
    summary["ok"] = findings.ok
    summary["errors"] = findings.errors
    summary["warnings"] = findings.warnings
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path, help="検証対象の JSON")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="解析元のファイル（box の範囲チェック用）",
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=None,
        help="エンドポイントの生レスポンス（--intermediate_save の出力）。取りこぼしの検出に使う",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="API のスキーマ（OpenAPI 定義、または JSON Schema）",
    )
    parser.add_argument("--expect-pages", type=int, default=None, help="想定ページ数")
    parser.add_argument(
        "--expect-page-numbers",
        default=None,
        help="想定する num_page のカンマ区切り（例: 0,2）",
    )
    parser.add_argument(
        "--report-json", type=Path, default=None, help="検証結果の出力先"
    )
    args = parser.parse_args()

    expect_page_numbers = None
    if args.expect_page_numbers:
        expect_page_numbers = [int(n) for n in args.expect_page_numbers.split(",")]

    summary = validate(
        args.json_path,
        input_path=args.input,
        schema_path=args.schema,
        expect_pages=args.expect_pages,
        expect_page_numbers=expect_page_numbers,
        raw_path=args.raw,
    )

    totals = {
        "tables": sum(page["n_tables"] for page in summary["pages"]),
        "words": sum(page["n_words"] for page in summary["pages"]),
        "paragraphs": sum(page["n_paragraphs"] for page in summary["pages"]),
    }
    summary["totals"] = totals

    print(
        f"{args.json_path}: pages={summary['n_pages']} tables={totals['tables']} "
        f"paragraphs={totals['paragraphs']} words={totals['words']}"
    )
    for message in summary["warnings"]:
        print(f"  WARN  {message}")
    for message in summary["errors"]:
        print(f"  ERROR {message}")
    print(f"  => {'OK' if summary['ok'] else 'NG'}")

    if args.report_json is not None:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
