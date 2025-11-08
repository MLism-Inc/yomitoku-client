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
    FollowedBy,
    Forward,
    Group,
    Literal,
    MatchFirst,
    OneOrMore,
    Optional,
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
    """License logical expression parser"""

    ParserElement.enable_packrat()

    # Operator definition (AND/OR are treated as operators regardless of case)
    AND = MatchFirst(
        [CaselessKeyword("AND"), Literal(";"), Literal(","), Literal("/")]
    ).setParseAction(lambda _: "AND")

    OR = CaselessKeyword("OR").setParseAction(lambda _: "OR")

    # License name (Annotation parentheses are OK, but not if they contain AND/OR)
    name_word = Word(alphanums + ".:+-")
    # License name (Concatenation of words and spaces. Excludes operator tokens AND/OR)
    simple_name = OneOrMore(((~AND) + (~OR) + name_word) | White(" ")).setParseAction(
        lambda t: re.sub(r" {2,}", " ", "".join(t))
    )

    def _build_phrase_expr(phrase: str):
        """
        Matches composite phrases in allowed_set
        Compares case-insensitively but returns the original text
        """
        # Normalize spaces to 1 or more, escape punctuation
        pattern = re.escape(" ".join(phrase.split()))

        # Flexible spacing: replace space with one or more arbitrary whitespace
        pattern = pattern.replace(r"\ ", r"\s+")

        # Case-insensitive, but return the original text
        # (?i) for case-insensitive, \b for word boundaries
        regex = rf"(?i)\b{pattern}\b"

        # pyparsing.Regex is compatible with the re module. The matched string is returned as is
        return Regex(regex).setParseAction(lambda t: str(t[0]).strip())

    # Phrases in allowed_set are prioritized as 1 token (case-insensitive)
    allowed_phrase = None
    if allowed_set:
        norm_phrases = {" ".join(p.split()) for p in allowed_set}
        # Extract composite phrases that contain and/or
        and_or_phrases = [
            p for p in norm_phrases if " and " in p.lower() or " or " in p.lower()
        ]
        and_or_phrases.sort(key=len, reverse=True)  # Longest match first
        if and_or_phrases:
            allowed_phrase = MatchFirst([_build_phrase_expr(p) for p in and_or_phrases])

    # Parenthesized annotation (content is free, nesting allowed, empty is OK)
    # Treated as annotation only when appended to the immediately preceding name
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
    # Parentheses are generally suppressed, but a sub-expression that starts with
    # double parentheses is wrapped one level and kept
    double_paren_subexpr = Group(
        Suppress("(") + Suppress("(") + expr + Suppress(")") + Suppress(")")
    ).setParseAction(lambda t: [t[0]])

    # (name) should behave like just name, without extra grouping
    name_in_parens = (Suppress("(") + license_name + Suppress(")")).setParseAction(
        lambda t: t[0]
    )

    single_paren_subexpr = Group(
        Suppress("(") + ~FollowedBy(Literal("(")) + expr + Suppress(")")
    ).setParseAction(
        lambda _, _2, toks: toks.asList()[0]
        if isinstance(toks, ParseResults)
        else toks[0]
    )
    operand = (
        double_paren_subexpr | name_in_parens | license_name | single_paren_subexpr
    )

    expr <<= infixNotation(
        operand,
        [
            (AND, 2, opAssoc.LEFT),
            (OR, 2, opAssoc.LEFT),
        ],
    )

    # If multiple ORs are present, they are nested left-associatively (AND remains as is)
    def _nest_or(node):
        if isinstance(node, list):
            node = [_nest_or(x) for x in node]
            # Convert [x, 'OR', y, 'OR', z, ...] to [[x,'OR',y], 'OR', z, ...] stepwise
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

    # Root interprets in order: entire input wrapped, then expression, then pure name
    # StringEnd is added to each option to ensure consumption until the end
    name_or_paren = Forward()
    name_or_paren <<= license_name | (Suppress("(") + name_or_paren + Suppress(")"))

    # Start: entire input wrapped once in parentheses, or plain expr/name
    wrapped_all = Group(Suppress("(") + expr + Suppress(")")) + StringEnd()
    start = wrapped_all | (expr + StringEnd()) | (name_or_paren + StringEnd())

    def _flatten_simple_wrapped(s, _, toks):
        """
        Only for "simple name entirely wrapped in parentheses",
        collapse the nesting to one level.
        Do not collapse logical expressions (containing AND/OR) or compound structures.
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
        # - If top-level operator is OR, collapse one level: ((X OR ...)) -> [[...]]
        # - If top-level operator is AND and RHS is itself nested (contains a
        #   deeper list), collapse one level: (A AND (B OR (C AND D))) -> [[...]]
        if (
            isinstance(v, list)
            and len(v) == 1
            and isinstance(v[0], list)
            and len(v[0]) == 1
            and isinstance(v[0][0], list)
        ):
            expr_list = v[0][0]
            if isinstance(expr_list, list) and len(expr_list) == 3:
                op_tok = expr_list[1]

                # Do not collapse if the whole parenthesized input begins
                # with a double "((", which should preserve one extra
                # grouping level for this OR group.
                if (
                    isinstance(op_tok, str)
                    and op_tok.upper() == "OR"
                    and not s.strip().startswith("((")
                ):
                    return [expr_list]
                if isinstance(expr_list[2], list) and any(
                    isinstance(e, list) for e in expr_list[2]
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
            and v[0][1].upper() == "AND"
        ):
            rhs = v[0][2]
            if (
                isinstance(rhs, list)
                and len(rhs) == 3
                and isinstance(rhs[0], list)
                and not (
                    isinstance(rhs, list) and len(rhs) == 1 and isinstance(rhs[0], list)
                )
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
                if ch == "(":
                    depth0 += 1
                elif ch == ")":
                    depth0 -= 1
                elif depth0 == 0 and source[i : i + 3].lower() == "and":
                    prev = source[i - 1] if i - 1 >= 0 else " "
                    nxt = source[i + 3] if i + 3 < n else " "
                    if prev.isspace() and nxt.isspace():
                        j = i + 3
                        while j < n and source[j].isspace():
                            j += 1
                        return j + 1 < n and source[j] == "(" and source[j + 1] == "("
                i += 1
            return False

        if (
            isinstance(v, list)
            and len(v) == 1
            and isinstance(v[0], list)
            and len(v[0]) == 3
            and isinstance(v[0][1], str)
            and v[0][1].upper() == "AND"
            and _rhs_starts_with_double_paren(s)
        ):
            rhs = v[0][2]
            if not (
                isinstance(rhs, list) and len(rhs) == 1 and isinstance(rhs[0], list)
            ):
                v[0][2] = [rhs]
                return v
        # Do not collapse [[expr]] -> [expr]; tests expect one extra wrapper
        # when the entire input is wrapped in parentheses around an expression.

        # Unpack single-element lists like [[[["MIT"]]]]
        cur = v
        depth = 0
        while isinstance(cur, list) and len(cur) == 1:
            cur = cur[0]
            depth += 1

        # --- Flattening condition ---
        # (1) The outermost layer was entirely wrapped in parentheses
        # (2) The content is purely str (simple name without AND/OR etc.)
        # Only then, flatten.
        if depth >= 1 and isinstance(cur, str):
            return [cur]

        # Or the entire list is a single string like ["MIT License (X11)"]
        if depth >= 1 and isinstance(cur, list) and len(cur) == 1:
            return [cur[0]]

        # No additional whole-input normalization here; wrapped_all handles it
        return v

    start.add_parse_action(_flatten_simple_wrapped)
    return start


def eval_expr(parsed, allowed_set: set[str]) -> bool:
    """
    Recursively evaluates the pyparsing parse tree (ParseResults or list)
    """

    # Leaf: If it's a string (assumes the allowed set is lowercased externally,
    # but allows case-insensitive comparison for compatibility)
    if isinstance(parsed, str):
        return (
            parsed in allowed_set
            or parsed.lower() in allowed_set
            or parsed.upper() in allowed_set
        )

    # Convert ParseResults to list
    if isinstance(parsed, ParseResults):
        parsed = parsed.asList()

    # Unwrap single-element nesting and recurse
    if len(parsed) == 1:
        return eval_expr(parsed[0], allowed_set)

    # Exceptionally, allow a 3-element sequence of name + AND/OR + name
    # to be treated as a single phrase (e.g., "Research and Development License", "... or later")
    # If the phrase is in the allowed set, treat it as True
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

    # Composite expression case
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
            raise ValueError(f"Unknown operator: {op}")

        i += 2

    return left


def check_licenses(
    licenses: list[str], allowed_set: set[str]
) -> tuple[dict[str, bool], list[list[str]]]:
    """
    Returns whether packages with each license in licenses can be used
    with the licenses allowed in allowed_set
    """

    parser = build_parser(allowed_set)
    license_ok: dict[str, bool] = {}
    parse_results: list[list[str]] = []

    for lic in licenses:
        if not lic:
            click.echo("[WARN] License information is empty")
            license_ok[lic] = False
            continue

        if lic in allowed_set:
            license_ok[lic] = True
            continue

        try:
            parsed = parser.parseString(lic, parseAll=True).asList()[0]
            parse_results.append(parsed)

            # Pass the allowed license list normalized to lowercase
            ok = eval_expr(parsed, {s.lower() for s in allowed_set})
        except Exception as e:
            click.echo(f"[WARN] Failed to parse license expression ({lic}) -> {e}")
            ok = False

        license_ok[lic] = bool(ok)

    return license_ok, parse_results


@click.command()
@click.option(
    "--allow",
    "-a",
    multiple=True,
    required=True,
    help="Specify multiple allowed licenses. Example: -a Apache-2.0 -a BSD-3-Clause -a MIT",
)
def main(allow: list[str]):
    """
    Retrieves the output of uv run pip-licenses and checks if all licenses
    are satisfied within the allowed list ALLOW
    """

    uv_path = shutil.which("uv")
    if uv_path is None:
        click.echo(
            "❌ uv command not found. Please check your installation.", err=True
        )
        sys.exit(1)

    # Read pip-licenses output
    try:
        # Ruff S603/S607 warning: Can be ignored for fixed safe command
        result = subprocess.run(  # noqa: S603,S607
            [uv_path, "run", "pip-licenses", "--format=csv"],
            check=True,
            capture_output=True,
            text=True,
        )

        df = pd.read_csv(io.StringIO(result.stdout))
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to run pip-licenses: {e}", err=True)
        sys.exit(e.returncode)

    allowed_set = set(allow)

    click.echo(f"Allowed licenses: {', '.join(sorted(allowed_set))}")
    click.echo("-" * 70)

    # Check only unique values in the 'License' column
    unique_licenses = list(df["License"].astype(str).unique())
    license_ok, parse_results = check_licenses(unique_licenses, allowed_set)

    click.echo("Parse results")

    for s in parse_results:
        click.echo(s)

    click.echo("-" * 70)

    # Map results to all packages
    df["LicenseOK"] = df["License"].map(license_ok)
    all_ok = df["LicenseOK"].all()

    # List packages with disallowed licenses
    bad_rows = df.loc[~df["LicenseOK"]]
    for lic, group in bad_rows.groupby("License"):
        pkgs = ", ".join(group["Name"].tolist())
        click.echo(f"❌ {lic} : {pkgs}")

    click.echo("-" * 70)
    click.echo(
        "Result: "
        + (
            "✅ All are allowed"
            if all_ok
            else "❌ Some licenses are not allowed"
        )
    )
    sys.exit(0 if all_ok else 2)


if __name__ == "__main__":
    main()