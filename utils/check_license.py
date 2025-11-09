import io
import re
import shutil
import subprocess
import sys
import unicodedata
from typing import Any

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


def normalize_str(s: str) -> str:
    """Normalize string (case, spaces, full-width characters, and Unicode normalization)"""
    s = s.strip()
    s = s.replace("–", "-").replace("_", "-")
    s = unicodedata.normalize(
        "NFKC", s
    )  # Normalize full-width characters and composite characters
    s = re.sub(r"\s+", " ", s)  # Unify spaces
    return s.lower()


def build_allowed_phrase(phrases: set[str]) -> ParserElement | None:
    """find allowed phrases"""
    if not phrases:
        return None

    normalized = {" ".join(p.split()) for p in phrases}
    candidates = [p for p in normalized if re.search(r"\b(and|or)\b", p, flags=re.I)]
    if not candidates:
        return None

    # Greedy: try to match longer phrases first
    candidates.sort(key=len, reverse=True)

    def as_regex(phrase: str) -> ParserElement:
        words = phrase.split()
        escaped = [re.escape(w) for w in words]
        pattern = r"\s+".join(escaped)
        return Regex(rf"(?i)\b{pattern}\b").setParseAction(lambda t: str(t[0]).strip())

    return MatchFirst([as_regex(p) for p in candidates])


def build_parser(allowed_set: set[str]) -> ParserElement:
    """
    Build a parser for license expressions.

    Grammar highlights:
    - Operators: AND (also ';', ',', '/'), OR.
    - License names: words (including .:+-), optionally followed by an
      annotation in parentheses, e.g. "MIT (X11)".
    - Parentheses for grouping: support single and multiple nestings like
      (A), ((A)), etc., without confusing annotations with grouping.
    - Certain composite phrases listed in `allowed_set` that contain logical
      keywords (e.g. "LGPL v2.1 or later") are treated as a single token.
    """

    ParserElement.enable_packrat()

    # --- Operators ---------------------------------------------------------
    AND = MatchFirst(
        [CaselessKeyword("AND"), Literal(";"), Literal(","), Literal("/")]
    ).setParseAction(lambda _: "AND")
    OR = CaselessKeyword("OR").setParseAction(lambda _: "OR")

    # --- License name and annotation --------------------------------------
    name_word = Word(alphanums + ".:+-")

    # Join tokens as a single name while ignoring operator tokens
    def _join_and_collapse_spaces(toks: ParseResults | list[str]) -> str:
        joined = "".join(toks)
        return re.sub(r" {2,}", " ", joined)

    simple_name = OneOrMore(((~AND) + (~OR) + name_word) | White(" ")).setParseAction(
        _join_and_collapse_spaces
    )

    # Annotation is any parenthesized text (including nested), captured verbatim
    annotation = originalTextFor(nestedExpr(opener="(", closer=")"))

    allowed_phrase = build_allowed_phrase(allowed_set)

    name_with_annotation = Combine(simple_name + Optional(annotation)).setParseAction(
        lambda t: str(t[0]).strip()
    )

    license_name = MatchFirst(
        filter(None, [allowed_phrase, name_with_annotation])
    ).setParseAction(lambda t: str(t[0]).strip())

    # --- Expressions and parentheses --------------------------------------
    expr = Forward()

    expr <<= infixNotation(
        license_name | Group(Suppress("(") + expr + Suppress(")")),
        [
            (AND, 2, opAssoc.LEFT),
            (OR, 2, opAssoc.LEFT),
        ],
    )

    return expr + StringEnd()


def eval_expr(parsed: ParseResults | list[Any] | str, allowed_set: set[str]) -> bool:
    """
    Recursively evaluates the pyparsing parse tree (ParseResults or list)
    allowed_set: set that includes normalized strs
    """

    # Leaf node: compare as a normalized string.
    if isinstance(parsed, str):
        return normalize_str(parsed) in allowed_set

    # Convert ParseResults to list
    if isinstance(parsed, ParseResults):
        parsed = parsed.asList()

    # Unwrap single-element nesting and recurse
    if len(parsed) == 1:
        return eval_expr(parsed[0], allowed_set)

    # Composite expression case
    left = eval_expr(parsed[0], allowed_set)
    for i in range(1, len(parsed), 2):
        op = parsed[i]
        right = eval_expr(parsed[i + 1], allowed_set)
        if op.upper() == "AND":
            left = left and right
        elif op.upper() == "OR":
            left = left or right
        else:
            raise ValueError(f"Unknown operator: {op}")

    return left


def check_licenses(
    licenses: list[str], allowed_set: set[str]
) -> tuple[dict[str, bool], list[list[str]]]:
    """
    Returns whether packages with each license in licenses can be used
    with the licenses allowed in allowed_set
    """

    normalized_allowed_set = {normalize_str(s) for s in allowed_set}
    parser = build_parser(allowed_set)
    license_ok: dict[str, bool] = {}
    parse_results: list[list[str]] = []

    for lic in licenses:
        if not lic:
            click.echo("[WARN] License information is empty")
            license_ok[lic] = False
            parse_results.append([lic])
            continue

        if normalize_str(lic) in normalized_allowed_set:
            license_ok[lic] = True
            parse_results.append([lic])
            continue

        ok = False
        try:
            parsed = parser.parseString(lic, parseAll=True).asList()[0]
            parse_results.append(parsed)

            # Pass the allowed license list normalized
            ok = eval_expr(parsed, normalized_allowed_set)
        except ParseException as e:
            click.echo(
                f"[WARN] Syntax error in license expression ({lic}): {e}", err=True
            )
        except Exception as e:
            click.echo(
                f"[WARN] Unexpected error for ({lic}): {type(e).__name__}: {e}",
                err=True,
            )

        license_ok[lic] = bool(ok)

    return license_ok, parse_results


def run_license_check(allow: list[str], debug: bool = False) -> int:
    """
    Retrieves the output of uv run pip-licenses and checks if all licenses
    are satisfied within the allowed list ALLOW
    """

    uv_path = shutil.which("uv")
    if uv_path is None:
        click.echo("❌ uv command not found. Please check your installation.", err=True)
        return 1

    # Read pip-licenses output
    try:
        cmd = [uv_path, "run", "pip-licenses", "--format=csv"]
        # Ruff S603/S607 warning: Can be ignored for fixed safe command
        result = subprocess.run(  # noqa: S603,S607
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )

        df = pd.read_csv(io.StringIO(result.stdout))
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to run pip-licenses: {e}", err=True)
        return e.returncode

    allowed_set = set(allow)

    click.echo(f"Allowed licenses: {', '.join(sorted(allowed_set))}")

    # Check only unique values in the 'License' column
    unique_licenses = list(df["License"].astype(str).unique())
    license_ok, parse_results = check_licenses(unique_licenses, allowed_set)

    if debug:
        click.echo("-" * 70)
        click.echo("Parse Results\n")

        for s in parse_results:
            click.echo(s)

    # Map results to all packages
    df["LicenseOK"] = df["License"].map(license_ok)
    all_ok = df["LicenseOK"].all()

    # List packages with disallowed licenses
    bad_rows = df.loc[~df["LicenseOK"]]

    if debug and len(bad_rows):
        click.echo("-" * 70)

    for lic, group in bad_rows.groupby("License"):
        pkgs = ", ".join(group["Name"].tolist())
        click.echo(f"❌ {lic} : {pkgs}", err=True)

    click.echo("-" * 70)
    click.echo(
        "Result: "
        + ("✅ All are allowed" if all_ok else "❌ Some licenses are not allowed"),
    )
    return 0 if all_ok else 2


@click.command()  # type: ignore[misc]
@click.option(
    "--allow",
    "-a",
    multiple=True,
    required=True,
    help="Specify multiple allowed licenses. Example: -a Apache-2.0 -a BSD-3-Clause -a MIT",
)  # type: ignore[misc]
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    default=False,
    help="Enable debug mode. Shows parsed strings when active.",
)  # type: ignore[misc]
def main(allow: list[str], debug: bool) -> None:
    sys.exit(run_license_check(allow, debug))


if __name__ == "__main__":
    main()
