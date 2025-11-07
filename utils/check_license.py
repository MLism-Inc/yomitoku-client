import io
import re
import shutil
import subprocess
import sys

import click
import pandas as pd
from pyparsing import (
    CaselessKeyword,
    Combine,
    Forward,
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParserElement,
    ParseResults,
    Suppress,
    White,
    Word,
    alphanums,
    infixNotation,
    opAssoc,
)


def build_parser() -> ParserElement:
    """ライセンス論理式パーサー"""

    ParserElement.enable_packrat()

    # 演算子定義
    AND = MatchFirst(
        [CaselessKeyword("AND"), Literal(";"), Literal(","), Literal("/")]
    ).setParseAction(lambda _: "AND")

    OR = CaselessKeyword("OR").setParseAction(lambda _: "OR")

    # ライセンス名（注釈括弧はOK、ただし中にAND/ORがあればNG）
    name_word = Word(alphanums + ".:+-")
    simple_name = OneOrMore(~AND + ~OR + name_word | White(" ")).setParseAction(
        lambda t: re.sub(r" {2,}", " ", "".join(t))
    )

    # 括弧付き注釈（AND/ORなし）
    annotation = Group(
        Suppress("(")
        + OneOrMore(~AND + ~OR + Word(alphanums + ".:+- "))
        + Suppress(")")
    ).setParseAction(lambda t: "(" + " ".join(t[0]).strip() + ")")

    license_name = Combine(simple_name + Optional(annotation)).setParseAction(
        lambda t: str(t[0]).strip()
    )

    expr = Forward()
    operand = license_name | (Suppress("(") + expr + Suppress(")"))

    expr <<= infixNotation(
        operand,
        [
            (AND, 2, opAssoc.LEFT),
            (OR, 2, opAssoc.LEFT),
        ],
    )

    # --- 結果整形: 余計なネストを除去 ---
    def normalize(tree):
        if isinstance(tree, list):
            if len(tree) == 1 and isinstance(tree[0], list):
                return normalize(tree[0])
            return [normalize(x) for x in tree]
        return tree

    return expr.add_parse_action(lambda t:normalize(t.asList()))


def eval_expr(parsed, allowed_set: set[str]) -> bool:
    """
    pyparsingの構文木（ParseResultsまたはリスト）を再帰的に評価する
    """

    # 末端: 文字列の場合
    if isinstance(parsed, str):
        # 小文字に正規化してから許可したライセンス一覧に含まれるかチェックする
        return parsed.lower() in allowed_set

    # ParseResults → リストに変換
    if isinstance(parsed, ParseResults):
        parsed = parsed.asList()

    # 単一要素の入れ子を解いて再帰
    if len(parsed) == 1:
        return eval_expr(parsed[0], allowed_set)

    # 複合式の場合
    left = eval_expr(parsed[0], allowed_set)
    i = 1
    while i < len(parsed):
        op = parsed[i]
        right = eval_expr(parsed[i + 1], allowed_set)
        if op.upper() == "AND":
            left = left and right
        elif op.upper() == "OR":
            left = left or right
        else:
            raise ValueError(f"未知の演算子: {op}")

        i += 2

    return left


def check_licenses(
    licenses: list[str], allowed_set: set[str]
) -> tuple[dict[str, bool], list[list[str]]]:
    """
    allowed_setで許可されているライセンスでlicensesの各ライセンスのパッケージを
    使うことができるかを返す
    """

    parser = build_parser()
    license_ok: dict[str, bool] = {}
    parse_results: list[list[str]] = []

    for lic in licenses:
        if not lic:
            click.echo("[WARN] ライセンス情報が空欄")
            license_ok[lic] = False
            continue

        if lic in allowed_set:
            license_ok[lic] = True
            continue

        try:
            parsed = parser.parseString(lic, parseAll=True).asList()[0]
            parse_results.append(parsed)

            # 許可したライセンスリストを小文字に正規化して渡す
            ok = eval_expr(parsed, {s.lower() for s in allowed_set})
        except Exception as e:
            click.echo(f"[WARN] ライセンス式を解析できません ({lic}) → {e}")
            ok = False

        license_ok[lic] = bool(ok)

    return license_ok, parse_results


@click.command()
@click.option(
    "--allow",
    "-a",
    required=True,
    help=(
        "許可するライセンスをスペース区切りで指定 例: -a 'Apache-2.0 BSD-3-Clause MIT'"
    ),
)
def main(allow: str):
    """
    uv run pip-licenses の出力を取得し、
    すべてのライセンスが許可リスト ALLOW 内で満たされているかチェックする
    """

    uv_path = shutil.which("uv")
    if uv_path is None:
        click.echo(
            "❌ uv コマンドが見つかりません。インストールを確認してください。", err=True
        )
        sys.exit(1)

    # pip-licensesの出力を読み取る
    try:
        # Ruff S603/S607警告: 固定安全コマンドのため無視してよい
        result = subprocess.run(  # noqa: S603,S607
            [uv_path, "run", "pip-licenses", "--format=csv"],
            check=True,
            capture_output=True,
            text=True,
        )

        df = pd.read_csv(io.StringIO(result.stdout))
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ pip-licenses の実行に失敗しました: {e}", err=True)
        sys.exit(e.returncode)

    allowed_set = set(allow.split())

    click.echo(f"許可ライセンス: {', '.join(sorted(allowed_set))}")
    click.echo("-" * 70)

    # License列のユニーク値のみを対象にチェック
    unique_licenses = list(df["License"].astype(str).unique())
    license_ok, parse_results = check_licenses(unique_licenses, allowed_set)

    click.echo("パースの結果")

    for s in parse_results:
        click.echo(s)

    click.echo("-" * 70)

    # 全パッケージについて結果をマッピング
    df["LicenseOK"] = df["License"].map(license_ok)
    all_ok = df["LicenseOK"].all()

    # 不許可ライセンスを持つパッケージ列挙
    bad_rows = df.loc[~df["LicenseOK"]]
    for lic, group in bad_rows.groupby("License"):
        pkgs = ", ".join(group["Name"].tolist())
        click.echo(f"❌ {lic} : {pkgs}")

    click.echo("-" * 70)
    click.echo(
        "結果: "
        + (
            "✅ すべて許可されています"
            if all_ok
            else "❌ 許可されないライセンスがあります"
        )
    )
    sys.exit(0 if all_ok else 2)


if __name__ == "__main__":
    main()
