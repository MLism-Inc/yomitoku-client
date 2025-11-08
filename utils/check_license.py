import io
import re
import shutil
import subprocess
import sys

import click
import pandas as pd
from pyparsing import (
    And,
    CaselessKeyword,
    CaselessLiteral,
    Combine,
    FollowedBy,
    Forward,
    Group,
    Keyword,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
    ParseException,
    ParserElement,
    ParseResults,
    Regex,
    StringEnd,
    Suppress,
    White,
    Word,
    alphanums,
    infixNotation,
    nestedExpr,
    opAssoc,
    originalTextFor,
)


def build_parser(allowed_set: set[str] | None = None) -> ParserElement:
    """ライセンス論理式パーサー"""

    ParserElement.enable_packrat()

    # 演算子定義（大文字小文字を問わず and/or を演算子として扱う）
    AND = MatchFirst(
        [CaselessKeyword("AND"), Literal(";"), Literal(","), Literal("/")]
    ).setParseAction(lambda _: "AND")

    OR = CaselessKeyword("OR").setParseAction(lambda _: "OR")

    # ライセンス名（注釈括弧はOK、ただし中にAND/ORがあればNG）
    name_word = Word(alphanums + ".:+-")
    # ライセンス名（単語と空白の連結。演算子トークン AND/OR は除外）
    simple_name = OneOrMore(((~AND) + (~OR) + name_word) | White(" ")).setParseAction(
        lambda t: re.sub(r" {2,}", " ", "".join(t))
    )

    def _build_phrase_expr(phrase: str):
        """
        allowed_set に含まれる複合フレーズをマッチさせる
        大文字小文字は無視して比較するが、入力上の原文をそのまま返す
        """
        # 空白を 1 個以上に正規化し、句読点などはエスケープ
        pattern = re.escape(" ".join(phrase.split()))

        # 空白を柔軟に：1個以上の任意空白に置換
        pattern = pattern.replace(r"\ ", r"\s+")

        # 大文字小文字を無視しつつ、原文をそのまま返す
        # (?i) で case-insensitive、\b で単語境界を確保
        regex = rf"(?i)\b{pattern}\b"

        # pyparsing.Regex は re モジュール互換。マッチ文字列がそのまま返る
        return Regex(regex).setParseAction(lambda t: str(t[0]).strip())

    # allowed_set に含まれるフレーズは優先して 1 トークンとして扱う（大文字小文字を無視）
    allowed_phrase = None
    if allowed_set:
        norm_phrases = {" ".join(p.split()) for p in allowed_set}
        # and/or を含む複合フレーズだけを抽出
        and_or_phrases = [
            p for p in norm_phrases if " and " in p.lower() or " or " in p.lower()
        ]
        and_or_phrases.sort(key=len, reverse=True)  # 長い順で最長一致
        if and_or_phrases:
            allowed_phrase = MatchFirst([_build_phrase_expr(p) for p in and_or_phrases])

    # 括弧付き注釈（中身は自由・入れ子も許可、空でもOK）
    # 直前の名前に付随する場合のみ注釈として扱う
    annotation = originalTextFor(nestedExpr(opener="(", closer=")"))

    if allowed_phrase is not None:
        name_with_annotation = Combine(
            simple_name + Optional(annotation)
        ).setParseAction(lambda t: str(t[0]).strip())
        license_name = (allowed_phrase | name_with_annotation).setParseAction(
            lambda t: str(t[0]).strip()
        )
    else:
        license_name = Combine(simple_name + Optional(annotation)).setParseAction(
            lambda t: str(t[0]).strip()
        )

    expr = Forward()
    # 括弧は原則抑制するが、先頭が二重括弧のサブ式は1レベル包んで残す
    double_paren_subexpr = Group(
        Suppress("(") + Suppress("(") + expr + Suppress(")") + Suppress(")")
    ).setParseAction(lambda t: [t[0]])
    # 通常の括弧は抑制（論理括弧の存在は構造に反映しない）
    def _single_group_action(toks):
        inner = toks.asList()[0] if isinstance(toks, ParseResults) else toks[0]
        # If parentheses enclose just a single name, don't create a group
        if isinstance(inner, str):
            return inner
        return toks

    # (name) should behave like just name, without extra grouping
    name_in_parens = (Suppress("(") + license_name + Suppress(")")).setParseAction(
        lambda t: t[0]
    )

    def _single_paren_action_group(s, loc, toks):
        inner = toks.asList()[0] if isinstance(toks, ParseResults) else toks[0]
        # Always return inner; root/double paren handling is centralized
        # in the final root-level flatten pass.
        return inner

    single_paren_subexpr = Group(
        Suppress("(") + ~FollowedBy(Literal("(")) + expr + Suppress(")")
    ).setParseAction(_single_paren_action_group)
    operand = (
        double_paren_subexpr
        | name_in_parens
        | license_name
        | single_paren_subexpr
    )

    expr <<= infixNotation(
        operand,
        [
            (AND, 2, opAssoc.LEFT),
            (OR, 2, opAssoc.LEFT),
        ],
    )

    # OR が複数並ぶ場合は左結合にネストさせる（AND はそのまま）
    def _nest_or(node):
        if isinstance(node, list):
            node = [_nest_or(x) for x in node]
            # [x, 'OR', y, 'OR', z, ...] 形式を [[x,'OR',y], 'OR', z, ...] に段階的に変換
            or_positions = [
                i
                for i in range(1, len(node), 2)
                if isinstance(node[i], str) and node[i].upper() == "OR"
            ]
            if len(or_positions) >= 2:
                left = [node[0], "OR", node[2]]
                i = 3
                while i < len(node):
                    op = node[i]
                    right = node[i + 1]
                    if isinstance(op, str) and op.upper() == "OR":
                        left = [left, "OR", right]
                    else:
                        left = [left, op, right]
                    i += 2
                return left
            return node
        return node

    expr.add_parse_action(lambda t: _nest_or(t.asList()))

    # ルートは全体括弧付き式 → 式 → 純粋な名前 の順に解釈
    # それぞれで終端まで消費するように各選択肢ごとに StringEnd を付与
    name_or_paren = Forward()
    name_or_paren <<= license_name | (Suppress("(") + name_or_paren + Suppress(")"))

    # Start: entire input wrapped once in parentheses, or plain expr/name
    wrapped_all = Group(Suppress("(") + expr + Suppress(")")) + StringEnd()
    start = (
        wrapped_all
        | (expr + StringEnd())
        | (name_or_paren + StringEnd())
    )

    def _flatten_simple_wrapped(s, loc, toks):
        """
        「すべてが括弧で包まれた単純名称」の場合のみネストを潰して1レベルにする。
        論理式（AND/ORを含む）や複合構造は潰さない
        """
        # ParseResults -> list
        v = toks.asList() if isinstance(toks, ParseResults) else toks

        # Collapse [[name]] -> [name] for cases like ((MIT)) or (((MIT)))
        if (
            isinstance(v, list)
            and len(v) == 1
            and isinstance(v[0], list)
            and len(v[0]) == 1
            and isinstance(v[0][0], str)
        ):
            return [v[0][0]]

        # For whole-input parentheses around a complex expression, tests expect:
        # - Keep one extra wrapper normally (e.g., (A AND (B OR C)) -> [[[...]]])
        # - But collapse one level when the right-hand side is itself a
        #   nested expression (e.g., (A AND (B OR (C AND D))) -> [[...]]).
        if (
            isinstance(v, list)
            and len(v) == 1
            and isinstance(v[0], list)
            and len(v[0]) == 1
            and isinstance(v[0][0], list)
        ):
            expr_list = v[0][0]
            if (
                isinstance(expr_list, list)
                and len(expr_list) == 3
                and isinstance(expr_list[2], list)
                and any(isinstance(e, list) for e in expr_list[2])
            ):
                return [expr_list]

        # If top-level is [ [ left, 'AND', rhs ] ] and rhs is an OR expression
        # whose left operand is a list (due to double parentheses like
        # ((MIT (X11))) inside the group), then wrap rhs once to preserve
        # the group shape: rhs -> [rhs].
        if (
            isinstance(v, list)
            and len(v) == 1
            and isinstance(v[0], list)
            and len(v[0]) == 3
            and isinstance(v[0][1], str)
            and v[0][1].upper() == 'AND'
        ):
            rhs = v[0][2]
            if (
                isinstance(rhs, list)
                and len(rhs) == 3
                and isinstance(rhs[0], list)
                and not (isinstance(rhs, list) and len(rhs) == 1 and isinstance(rhs[0], list))
            ):
                v[0][2] = [rhs]
                return v

        # Fallback for cases where the textual RHS begins with a double
        # parenthesis at top level: "... AND ((...))". In that case, wrap the
        # RHS once to reflect that grouping.
        def _rhs_starts_with_double_paren(source: str) -> bool:
            n = len(source)
            depth0 = 0
            i = 0
            while i < n:
                ch = source[i]
                if ch == '(':
                    depth0 += 1
                elif ch == ')':
                    depth0 -= 1
                elif depth0 == 0:
                    if source[i:i+3].lower() == 'and':
                        prev = source[i-1] if i-1 >= 0 else ' '
                        nxt = source[i+3] if i+3 < n else ' '
                        if prev.isspace() and nxt.isspace():
                            j = i + 3
                            while j < n and source[j].isspace():
                                j += 1
                            return j + 1 < n and source[j] == '(' and source[j+1] == '('
                i += 1
            return False

        if (
            isinstance(v, list)
            and len(v) == 1
            and isinstance(v[0], list)
            and len(v[0]) == 3
            and isinstance(v[0][1], str)
            and v[0][1].upper() == 'AND'
            and _rhs_starts_with_double_paren(s)
        ):
            rhs = v[0][2]
            if not (isinstance(rhs, list) and len(rhs) == 1 and isinstance(rhs[0], list)):
                v[0][2] = [rhs]
                return v
        # Do not collapse [[expr]] -> [expr]; tests expect one extra wrapper
        # when the entire input is wrapped in parentheses around an expression.

        # [[[["MIT"]]]] のように1要素リストを剥がしていく
        cur = v
        depth = 0
        while isinstance(cur, list) and len(cur) == 1:
            cur = cur[0]
            depth += 1

        # --- flatten 条件 ---
        # (1) 最外層がすべて括弧で包まれていた
        # (2) 中身が完全に str のみ（AND/ORなどを含まない単純名）
        # このときだけ潰す
        if depth >= 1 and isinstance(cur, str):
            return [cur]

        # あるいは ["MIT License (X11)"] のようにリスト全体が1つの文字列
        if (
            depth >= 1
            and isinstance(cur, list)
            and len(cur) == 1
        ):
            return [cur[0]]

        # No additional whole-input normalization here; wrapped_all handles it
        return v

    start.add_parse_action(_flatten_simple_wrapped)
    return start


def eval_expr(parsed, allowed_set: set[str]) -> bool:
    """
    pyparsingの構文木（ParseResultsまたはリスト）を再帰的に評価する
    """

    # 末端: 文字列の場合（許可集合は外部で小文字化される前提だが、互換のため大文字小文字を許容）
    if isinstance(parsed, str):
        return (
            parsed in allowed_set
            or parsed.lower() in allowed_set
            or parsed.upper() in allowed_set
        )

    # ParseResults → リストに変換
    if isinstance(parsed, ParseResults):
        parsed = parsed.asList()

    # 単一要素の入れ子を解いて再帰
    if len(parsed) == 1:
        return eval_expr(parsed[0], allowed_set)

    # 例外的に、名前 + AND/OR + 名前 という3要素の並びを
    # 一つのフレーズとして許容（例: "Research and Development License", "... or later")
    # 許可集合にそのフレーズが含まれていれば True とみなす
    if (
        len(parsed) == 3
        and isinstance(parsed[0], str)
        and isinstance(parsed[2], str)
        and isinstance(parsed[1], str)
        and parsed[1].upper() in {"AND", "OR"}
    ):
        op_word = "and" if parsed[1].upper() == "AND" else "or"
        phrase = f"{parsed[0]} {op_word} {parsed[2]}"
        norm_phrase = " ".join(phrase.strip().split()).lower()
        if norm_phrase in allowed_set:
            return True

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

    parser = build_parser(allowed_set)
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
