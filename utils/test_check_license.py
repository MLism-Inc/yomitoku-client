import pytest
from pyparsing import ParseException, ParseResults

from utils.check_license import build_parser, eval_expr


def normalize_tree(v):
    """Simplification of Redundant Syntax Trees"""
    if isinstance(v, ParseResults):
        v = v.asList()
    if not isinstance(v, list):
        return v
    v = [normalize_tree(x) for x in v]
    # [[X]] → X（ただしAND/OR式は保持）
    while (
        len(v) == 1
        and isinstance(v[0], list)
        and not (
            len(v[0]) == 3
            and isinstance(v[0][1], str)
            and v[0][1].upper() in ("AND", "OR")
        )
    ):
        v = v[0]
    return v[0] if len(v) == 1 else v


def parse(expr, _allowed_set=None):
    """
    Parses a license expression string into a nested list structure.

    Args:
        expr (str): The license expression string.
        _allowed_set (set, optional): Set of allowed license identifiers.

    Returns:
        list: The normalized parsed structure.
    """
    parser = build_parser(
        _allowed_set
        or {
            "apache-2.0",
            "mit",
            "bsd-3-clause",
            "gpl",
            "lgpl",
            "unlicense",
            "zlib",
            "mozilla public license 2.0 (mpl 2.0)",
            "apache software license",
            "bsd license",
            "the unlicense",
            "gnu lesser general public license v2.1 or later",
            "research and development license",
            "bsd license (3-clause clear license)",
            "mit license",
            "apache-2.0 (spdx)",
            "mit (x11)",
            # Added other annotated licenses used in tests for completeness
            "mit license (expat (2010 revision))",
            "bsd-3-clause (version-2.0.alpha)",
            "mit (compatible with or later)",
            "bsd-3-clause (3-clause)",
            "mit ()",
            "bsd 3-clause",  # License with spaces and dashes
        }
    )
    # The original tests used .asList() which returns [parsed_result]
    # We return the normalized list of results.
    result = normalize_tree(parser.parseString(expr, parseAll=True).asList())
    return result


# --- Parsing Tests ---


def test_simple_license_name():
    result = parse("Apache-2.0")
    assert result == "Apache-2.0"


def test_parenthesis_annotation():
    """Annotation parentheses (MPL 2.0) are not treated as logical parentheses"""
    result = parse("Mozilla Public License 2.0 (MPL 2.0)")
    assert result == "Mozilla Public License 2.0 (MPL 2.0)"


def test_simple_and_expression():
    result = parse("Apache-2.0 AND MIT")
    assert result == ["Apache-2.0", "AND", "MIT"]


def test_simple_or_expression():
    result = parse("BSD-3-Clause OR MIT")
    assert result == ["BSD-3-Clause", "OR", "MIT"]


def test_expression_with_parentheses():
    result = parse("(Apache-2.0 OR MIT) AND BSD-3-Clause")
    # infixNotation returns a nested list structure
    assert result == [["Apache-2.0", "OR", "MIT"], "AND", "BSD-3-Clause"]


def test_nested_parentheses():
    """Nested structure is processed correctly"""
    result = parse("(Apache-2.0 AND (MIT OR BSD-3-Clause))")
    assert result == ["Apache-2.0", "AND", ["MIT", "OR", "BSD-3-Clause"]]


def test_consecutive_operators():
    """Syntax error for consecutive AND/OR"""
    with pytest.raises(ParseException):
        parse("Apache-2.0 AND OR MIT")


def test_slash_as_and():
    """Treat slash delimiter as AND"""
    result = parse("Apache-2.0 / MIT")
    assert result == ["Apache-2.0", "AND", "MIT"]


def test_semicolon_as_and():
    """Treat semicolon delimiter as AND"""
    result = parse("MIT; BSD-3-Clause")
    assert result == ["MIT", "AND", "BSD-3-Clause"]


def test_annotation_not_confused_with_logic():
    """Do not treat as logical expression if AND is not inside parentheses"""
    expr = "MIT License (X11 Style)"
    result = parse(expr)
    assert result == "MIT License (X11 Style)"


def test_annotation_with_logic_inside():
    """Treat as logical parentheses if AND/OR are inside parentheses"""
    expr = "MIT AND (Apache-2.0 OR BSD-3-Clause)"
    result = parse(expr)
    assert result == ["MIT", "AND", ["Apache-2.0", "OR", "BSD-3-Clause"]]


# --- Evaluation Tests ---


def test_eval_simple_true():
    parsed = parse("Apache-2.0")
    assert eval_expr(parsed, {"apache-2.0"}) is True


def test_eval_simple_false():
    parsed = parse("MIT")
    assert eval_expr(parsed, {"apache-2.0"}) is False


def test_eval_and_expression():
    parsed = parse("Apache-2.0 AND MIT")
    assert eval_expr(parsed, {"apache-2.0", "mit"}) is True
    assert eval_expr(parsed, {"apache-2.0"}) is False


def test_eval_or_expression():
    parsed = parse("Apache-2.0 OR MIT")
    assert eval_expr(parsed, {"apache-2.0"}) is True
    assert eval_expr(parsed, {"mit"}) is True
    assert eval_expr(parsed, {"bsd-3-clause"}) is False


def test_eval_nested_expression():
    parsed = parse("(Apache-2.0 OR MIT) AND BSD-3-Clause")
    assert eval_expr(parsed, {"apache-2.0", "bsd-3-clause"}) is True
    assert eval_expr(parsed, {"mit", "bsd-3-clause"}) is True
    assert eval_expr(parsed, {"apache-2.0"}) is False


def test_eval_with_case_insensitivity():
    parsed = parse("APACHE-2.0 or mit")
    assert eval_expr(parsed, {"apache-2.0"}) is True
    assert eval_expr(parsed, {"mit"}) is True
    assert eval_expr(parsed, {"bsd"}) is False


def test_eval_with_slash_and_semicolon():
    parsed1 = parse("MIT / BSD-3-Clause")
    parsed2 = parse("MIT; BSD-3-Clause")
    assert eval_expr(parsed1, {"mit", "bsd-3-clause"}) is True
    assert eval_expr(parsed2, {"mit"}) is False


def test_eval_nested_and_or_mixed():
    """Complex expression like (A OR B) AND (C OR D)"""
    expr = "(Apache-2.0 OR MIT) AND (BSD-3-Clause OR Unlicense)"
    parsed = parse(expr)
    assert eval_expr(parsed, {"apache-2.0", "bsd-3-clause"}) is True
    assert eval_expr(parsed, {"mit", "unlicense"}) is True
    assert eval_expr(parsed, {"apache-2.0"}) is False


# --- Additional Tests (More Complex and Diverse Inputs) ---


def test_long_chained_expression():
    """Expression with many chained AND/OR. Assumes AND > OR precedence."""
    expr = "Apache-2.0 OR MIT AND BSD-3-Clause OR Unlicense AND Zlib"
    result = parse(expr)
    assert result == [
        "Apache-2.0",
        "OR",
        ["MIT", "AND", "BSD-3-Clause"],
        "OR",
        ["Unlicense", "AND", "Zlib"],
    ]


def test_multiple_levels_of_annotations():
    """Case where annotation exists at multiple levels"""
    expr = "MIT License (Expat (2010 Revision))"
    result = parse(expr)
    assert result == "MIT License (Expat (2010 Revision))"


def test_mixed_logic_and_annotations():
    """Complex logical expression including annotations"""
    expr = "(Apache-2.0 (SPDX)) AND (BSD-3-Clause OR MIT (X11))"
    result = parse(expr)
    assert result == [
        "Apache-2.0 (SPDX)",
        "AND",
        ["BSD-3-Clause", "OR", "MIT (X11)"],
    ]


def test_annotation_with_special_chars():
    """Annotation containing special characters like dots or hyphens"""
    expr = "BSD-3-Clause (version-2.0.alpha)"
    result = parse(expr)
    assert result == "BSD-3-Clause (version-2.0.alpha)"


def test_parentheses_with_extra_spaces():
    """Correct behavior even with extra spaces around parentheses"""
    expr = "(  Apache-2.0  OR  MIT  )  AND  BSD-3-Clause"
    result = parse(expr)
    assert result == [["Apache-2.0", "OR", "MIT"], "AND", "BSD-3-Clause"]


def test_nested_and_or_with_annotation():
    """Annotation license included in nested structure"""
    expr = "((MIT (X11)) OR (BSD-3-Clause AND Apache-2.0))"
    result = parse(expr)
    assert result == [
        "MIT (X11)",
        "OR",
        ["BSD-3-Clause", "AND", "Apache-2.0"],
    ]


def test_double_parentheses_pairs():
    """Double parentheses structure"""
    expr = "((Apache-2.0))"
    result = parse(expr)
    assert result == "Apache-2.0"


def test_or_with_slash_and_semicolon():
    """OR expression mixed with slash and semicolon. Assumes AND > OR precedence."""
    expr = "(MIT / BSD-3-Clause) OR Apache-2.0; Zlib"
    result = parse(expr)
    assert result == [
        ["MIT", "AND", "BSD-3-Clause"],
        "OR",
        ["Apache-2.0", "AND", "Zlib"],
    ]


def test_annotation_that_looks_like_operator():
    """Do not misidentify words like 'AND' or 'OR' inside annotation"""
    expr = "MIT (compatible with OR later)"
    result = parse(expr)
    assert result == "MIT (compatible with OR later)"


def test_weird_but_valid_spacing():
    """Irregular whitespace like spaces and newlines"""
    expr = "Apache-2.0  AND  \n  (MIT  OR  BSD-3-Clause)"
    result = parse(expr)
    assert result == ["Apache-2.0", "AND", ["MIT", "OR", "BSD-3-Clause"]]


def test_multiple_license_blocks():
    """Multiple blocks linked by logical OR"""
    expr = "(Apache-2.0 AND MIT) OR (BSD-3-Clause AND Zlib)"
    result = parse(expr)
    assert result == [
        ["Apache-2.0", "AND", "MIT"],
        "OR",
        ["BSD-3-Clause", "AND", "Zlib"],
    ]


def test_complex_annotation_and_or_mix():
    """Complex mix of annotation and logical expression"""
    expr = "(Apache-2.0 (spdx)) AND ((MIT (X11)) OR BSD-3-Clause (3-Clause))"
    result = parse(expr)
    # The original expected result implies normalization might simplify outer double parentheses
    assert result == [
        "Apache-2.0 (spdx)",
        "AND",
        ["MIT (X11)", "OR", "BSD-3-Clause (3-Clause)"],
    ]


def test_consecutive_and():
    """Syntax error for consecutive AND"""
    with pytest.raises(ParseException):
        parse("MIT AND AND BSD-3-Clause")


def test_consecutive_or():
    """Syntax error for consecutive OR"""
    with pytest.raises(ParseException):
        parse("Apache-2.0 OR OR MIT")


def test_extra_parentheses_pairs():
    """Balanced extra parentheses are OK"""
    expr = "(((MIT)))"
    result = parse(expr)
    assert result == "MIT"


def test_invalid_token_is_treated_as_error():
    """Invalid tokens like #invalid are treated as syntax errors"""
    expr = "#invalid"
    with pytest.raises(ParseException):
        parse(expr)


def test_empty_parentheses_treated_as_annotation():
    """Empty parentheses '()' are treated as an empty annotation"""
    expr = "MIT ()"
    result = parse(expr)
    assert result == "MIT ()"


def test_double_nested_and_or():
    """Multi-level nesting like (A AND (B OR (C AND D)))"""
    expr = "(Apache-2.0 AND (MIT OR (BSD-3-Clause AND Unlicense)))"
    result = parse(expr)
    assert result == [
        "Apache-2.0",
        "AND",
        ["MIT", "OR", ["BSD-3-Clause", "AND", "Unlicense"]],
    ]


def test_unbalanced_right_parenthesis():
    """Syntax error for extra right parenthesis"""
    with pytest.raises(ParseException):
        parse("Apache-2.0 OR MIT)")


def test_unbalanced_left_parenthesis():
    """Syntax error for extra left parenthesis"""
    with pytest.raises(ParseException):
        parse("(Apache-2.0 OR MIT")


def test_long_mixed_chain():
    """Long mixed expression: AND/OR/comma/semicolon mix. Assumes comma/semicolon -> AND, AND > OR precedence."""
    expr = "MIT, Apache-2.0; BSD-3-Clause OR Unlicense / Zlib"
    result = parse(expr)
    assert result == [
        ["MIT", "AND", "Apache-2.0", "AND", "BSD-3-Clause"],
        "OR",
        ["Unlicense", "AND", "Zlib"],
    ]


# --- Additional Tests (Handling of Spaces, Annotations, and Multi-Word Licenses) ---


def test_license_with_spaces():
    """License name containing spaces (e.g., Apache Software License)"""
    expr = "Apache Software License"
    result = parse(expr)
    assert result == "Apache Software License"


def test_license_with_spaces_and_and():
    """AND expression between license names containing spaces"""
    expr = "Apache Software License AND MIT License"
    result = parse(expr)
    assert result == ["Apache Software License", "AND", "MIT License"]


def test_license_with_version_and_annotation():
    """Annotation name (e.g., Mozilla Public License 2.0 (MPL 2.0))"""
    expr = "Mozilla Public License 2.0 (MPL 2.0)"
    result = parse(expr)
    assert result == "Mozilla Public License 2.0 (MPL 2.0)"


def test_license_with_or_later_text():
    """Long license name including 'or later' (e.g., LGPL v2.1 or later)"""
    expr = "GNU Lesser General Public License v2.1 or later"
    result = parse(expr)
    assert result == "GNU Lesser General Public License v2.1 or later"


def test_license_with_and_inside_name():
    """'and' inside the license name is not misidentified as logical AND"""
    expr = "Research and Development License"
    result = parse(expr)
    assert result == "Research and Development License"


def test_license_with_parenthetical_long_annotation():
    """Annotation including multiple words inside parentheses"""
    expr = "BSD License (3-Clause Clear License)"
    result = parse(expr)
    assert result == "BSD License (3-Clause Clear License)"


def test_license_with_leading_article():
    """License name including an article (The Unlicense)"""
    expr = "The Unlicense"
    result = parse(expr)
    assert result == "The Unlicense"


def test_license_with_dash_and_space_mix():
    """Name mixing dashes and spaces (BSD 3-Clause)"""
    expr = "BSD 3-Clause"
    result = parse(expr)
    assert result == "BSD 3-Clause"


def test_license_with_annotation_and_logic():
    """Logical expression including an annotated name"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) OR Apache-2.0"
    result = parse(expr)
    assert result == ["Mozilla Public License 2.0 (MPL 2.0)", "OR", "Apache-2.0"]


def test_license_with_spaces_and_parentheses_nested():
    """Mix of spaces, annotations, and logical parentheses"""
    expr = "(Apache Software License OR Mozilla Public License 2.0 (MPL 2.0)) AND BSD-3-Clause"
    result = parse(expr)
    assert result == [
        ["Apache Software License", "OR", "Mozilla Public License 2.0 (MPL 2.0)"],
        "AND",
        "BSD-3-Clause",
    ]


def test_simple_or_between_two_licenses():
    """Simple OR expression (MIT or Apache-2.0)"""
    expr = "MIT or Apache-2.0"
    result = parse(expr)
    assert result == ["MIT", "OR", "Apache-2.0"]


def test_simple_and_between_two_licenses():
    """Simple AND expression (GPL and LGPL)"""
    expr = "GPL and LGPL"
    result = parse(expr)
    assert result == ["GPL", "AND", "LGPL"]


# --- Complex Logical Expression Tests with Lowercase and/or ---


def test_lowercase_or_and_and_combination():
    """Complex expression mixing lowercase or/and. Assumes 'and' > 'or' precedence."""
    expr = "MIT and Apache-2.0 or BSD-3-Clause and Unlicense"
    result = parse(expr)
    assert result == [
        ["MIT", "AND", "Apache-2.0"],
        "OR",
        ["BSD-3-Clause", "AND", "Unlicense"],
    ]


def test_parenthesized_lowercase_logic():
    """Expression using lowercase and/or with parentheses"""
    expr = "(mit or apache-2.0) and (bsd-3-clause or unlicense)"
    result = parse(expr)
    assert result == [
        ["mit", "OR", "apache-2.0"],
        "AND",
        ["bsd-3-clause", "OR", "unlicense"],
    ]


def test_nested_lowercase_logic():
    """Nested lowercase and/or expression"""
    expr = "((mit or apache-2.0) and bsd-3-clause) or unlicense"
    result = parse(expr)
    assert result == [
        [["mit", "OR", "apache-2.0"], "AND", "bsd-3-clause"],
        "OR",
        "unlicense",
    ]


def test_mixed_case_logic_expression():
    """Composite expression with mixed case logic. Assumes AND > OR precedence."""
    expr = "MIT or Apache-2.0 AND bsd-3-clause Or unlicense And Zlib"
    result = parse(expr)
    assert result == [
        "MIT",
        "OR",
        ["Apache-2.0", "AND", "bsd-3-clause"],
        "OR",
        ["unlicense", "AND", "Zlib"],
    ]


# --- Lowercase and/or + Multi-Word License with Spaces or Annotation Tests ---


def test_lowercase_and_with_multiword_license():
    """Connecting multi-word license names with 'and'"""
    expr = "Apache Software License and MIT License"
    result = parse(expr)
    assert result == ["Apache Software License", "AND", "MIT License"]


def test_lowercase_or_with_multiword_license():
    """Connecting multi-word license names with 'or'"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) or Apache Software License"
    result = parse(expr)
    assert result == [
        "Mozilla Public License 2.0 (MPL 2.0)",
        "OR",
        "Apache Software License",
    ]


def test_lowercase_and_or_mixed_with_multiword():
    """Mixed lowercase and/or expression including multi-word licenses. Assumes 'and' > 'or' precedence."""
    expr = "Apache Software License or MIT License and BSD License"
    result = parse(expr)
    assert result == [
        "Apache Software License",
        "OR",
        ["MIT License", "AND", "BSD License"],
    ]


def test_parenthesized_lowercase_and_or_with_multiword():
    """Lowercase and/or expression combining parentheses and multi-word licenses"""
    expr = "(Apache Software License or MIT License) and (BSD License or Mozilla Public License 2.0 (MPL 2.0))"
    result = parse(expr)
    assert result == [
        ["Apache Software License", "OR", "MIT License"],
        "AND",
        ["BSD License", "OR", "Mozilla Public License 2.0 (MPL 2.0)"],
    ]


def test_complex_expression_with_and_inside_name_left():
    """License name containing 'and' appears on the left side"""
    expr = "Research and Development License OR MIT"
    result = parse(expr)
    assert result == ["Research and Development License", "OR", "MIT"]


def test_complex_expression_with_and_inside_name_middle():
    """License name containing 'and' appears in the middle. Assumes AND > OR precedence."""
    expr = "Apache-2.0 AND Research and Development License OR BSD-3-Clause"
    result = parse(expr)
    assert result == [
        ["Apache-2.0", "AND", "Research and Development License"],
        "OR",
        "BSD-3-Clause",
    ]


def test_complex_expression_with_and_inside_name_right():
    """License name containing 'and' appears on the right side"""
    expr = "MIT OR Research and Development License"
    result = parse(expr)
    assert result == ["MIT", "OR", "Research and Development License"]


def test_parenthesized_and_inside_name():
    """License name containing 'and' appears within parentheses"""
    expr = "(Apache-2.0 OR Research and Development License) AND BSD-3-Clause"
    result = parse(expr)
    assert result == [
        ["Apache-2.0", "OR", "Research and Development License"],
        "AND",
        "BSD-3-Clause",
    ]


def test_double_nested_and_inside_name():
    """License name containing 'and' appears within multi-level nesting"""
    expr = "(MIT OR (BSD-3-Clause AND Research and Development License))"
    result = parse(expr)
    assert result == [
        "MIT",
        "OR",
        ["BSD-3-Clause", "AND", "Research and Development License"],
    ]


def test_research_and_dev_with_apache_left():
    """Research and Development License on the left, combined with Apache Software License"""
    expr = "Research and Development License OR Apache Software License"
    result = parse(expr)
    assert result == [
        "Research and Development License",
        "OR",
        "Apache Software License",
    ]


def test_research_and_dev_with_apache_right():
    """Research and Development License on the right, combined with Apache Software License"""
    expr = "Apache Software License AND Research and Development License"
    result = parse(expr)
    assert result == [
        "Apache Software License",
        "AND",
        "Research and Development License",
    ]


def test_research_and_dev_with_mozilla_left():
    """Research and Development License on the left, combined with Mozilla Public License 2.0 (MPL 2.0)"""
    expr = "Research and Development License OR Mozilla Public License 2.0 (MPL 2.0)"
    result = parse(expr)
    assert result == [
        "Research and Development License",
        "OR",
        "Mozilla Public License 2.0 (MPL 2.0)",
    ]


def test_research_and_dev_with_mozilla_right():
    """Research and Development License on the right, combined with Mozilla Public License 2.0 (MPL 2.0)"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) AND Research and Development License"
    result = parse(expr)
    assert result == [
        "Mozilla Public License 2.0 (MPL 2.0)",
        "AND",
        "Research and Development License",
    ]


def test_research_and_dev_nested_with_apache_and_mozilla():
    """Multi-level nesting structure including Research and Development License (Apache + Mozilla combined)"""
    expr = "(Apache Software License OR (Mozilla Public License 2.0 (MPL 2.0) AND Research and Development License))"
    result = parse(expr)
    assert result == [
        "Apache Software License",
        "OR",
        [
            "Mozilla Public License 2.0 (MPL 2.0)",
            "AND",
            "Research and Development License",
        ],
    ]


def test_research_and_dev_middle_with_mixed_complex():
    """Research and Development License as an intermediate term in a complex logical expression. Assumes AND > OR precedence."""
    expr = "Apache Software License AND Research and Development License OR Mozilla Public License 2.0 (MPL 2.0)"
    result = parse(expr)
    assert result == [
        ["Apache Software License", "AND", "Research and Development License"],
        "OR",
        "Mozilla Public License 2.0 (MPL 2.0)",
    ]


def test_research_and_dev_parenthesized():
    """Logical expression where Research and Development License is enclosed in parentheses"""
    expr = "(Research and Development License OR Apache Software License) AND Mozilla Public License 2.0 (MPL 2.0)"
    result = parse(expr)
    assert result == [
        ["Research and Development License", "OR", "Apache Software License"],
        "AND",
        "Mozilla Public License 2.0 (MPL 2.0)",
    ]


def test_double_and_as_error():
    """Syntax error for consecutive 'and'"""
    expr = "MIT and and Apache-2.0"
    with pytest.raises(ParseException):
        parse(expr)


def test_and_inside_name_and_operator():
    """Pattern where a license name containing 'and' is followed by a logical AND"""
    expr = "Research and Development License and MIT"
    result = parse(expr)
    assert result == ["Research and Development License", "AND", "MIT"]


def test_operator_and_and_inside_name():
    """Pattern where a logical AND is followed by a license name containing 'and'"""
    expr = "MIT and Research and Development License"
    result = parse(expr)
    assert result == ["MIT", "AND", "Research and Development License"]


def test_nested_double_and():
    """Syntax error for consecutive 'and' inside parentheses"""
    expr = "(Apache-2.0 and and MIT)"
    with pytest.raises(ParseException):
        parse(expr)


def test_double_and_in_long_expression():
    """Syntax error where 'and and' is mixed into a complex expression"""
    expr = "Apache-2.0 or MIT and and BSD-3-Clause"
    with pytest.raises(ParseException):
        parse(expr)


def test_and_between_lgpl_and_rnd():
    """'AND' combination of GNU LGPL v2.1 or later and Research and Development License."""
    expr = "GNU Lesser General Public License v2.1 or later AND Research and Development License"
    result = parse(expr)
    assert result == [
        "GNU Lesser General Public License v2.1 or later",
        "AND",
        "Research and Development License",
    ]


def test_or_between_lgpl_and_rnd():
    """'OR' combination of GNU LGPL v2.1 or later and Research and Development License."""
    expr = "GNU Lesser General Public License v2.1 or later OR Research and Development License"
    result = parse(expr)
    assert result == [
        "GNU Lesser General Public License v2.1 or later",
        "OR",
        "Research and Development License",
    ]


def test_and_outer_or_inner_with_parentheses():
    """Parenthesized: Research and Development License AND (GNU LGPL v2.1 or later OR MIT)"""
    expr = "Research and Development License AND (GNU Lesser General Public License v2.1 or later OR MIT)"
    result = parse(expr)
    assert result == [
        "Research and Development License",
        "AND",
        [
            "GNU Lesser General Public License v2.1 or later",
            "OR",
            "MIT",
        ],
    ]


def test_triple_nested_and_or_with_annotation():
    """3-level nesting: ((MIT (X11)) OR ((BSD-3-Clause AND Apache-2.0) OR GPL-3.0-only))"""
    expr = "((MIT (X11)) OR ((BSD-3-Clause AND Apache-2.0) OR GPL-3.0-only))"
    result = parse(expr)
    assert result == [
        "MIT (X11)",
        "OR",
        [["BSD-3-Clause", "AND", "Apache-2.0"], "OR", "GPL-3.0-only"],
    ]


def test_four_nested_and_or_with_annotation():
    """4-level nesting: (((MIT (X11)) OR ((BSD-3-Clause AND Apache-2.0) OR GPL-3.0-only)) AND LGPL-2.1-or-later)"""
    expr = "(((MIT (X11)) OR ((BSD-3-Clause AND Apache-2.0) OR GPL-3.0-only)) AND LGPL-2.1-or-later)"
    result = parse(expr)
    assert result == [
        [
            "MIT (X11)",
            "OR",
            [["BSD-3-Clause", "AND", "Apache-2.0"], "OR", "GPL-3.0-only"],
        ],
        "AND",
        "LGPL-2.1-or-later",
    ]


def test_five_nested_and_or_with_annotation():
    """5-level nesting: ((((MIT (X11)) OR ((BSD-3-Clause AND Apache-2.0) OR GPL-3.0-only)) AND LGPL-2.1-or-later) OR CC-BY-4.0)"""
    expr = "((((MIT (X11)) OR ((BSD-3-Clause AND Apache-2.0) OR GPL-3.0-only)) AND LGPL-2.1-or-later) OR CC-BY-4.0)"
    result = parse(expr)
    assert result == [
        [
            [
                "MIT (X11)",
                "OR",
                [["BSD-3-Clause", "AND", "Apache-2.0"], "OR", "GPL-3.0-only"],
            ],
            "AND",
            "LGPL-2.1-or-later",
        ],
        "OR",
        "CC-BY-4.0",
    ]


def test_single_paren():
    """1-level parentheses: (aaa)"""
    expr = "(aaa)"
    result = parse(expr)
    assert result == "aaa"


def test_double_paren():
    """2-level parentheses: ((aaa))"""
    expr = "((aaa))"
    result = parse(expr)
    assert result == "aaa"


def test_triple_paren():
    """3-level parentheses: (((aaa)))"""
    expr = "(((aaa)))"
    result = parse(expr)
    assert result == "aaa"


def test_quad_paren():
    """4-level parentheses: ((((aaa))))"""
    expr = "((((aaa))))"
    result = parse(expr)
    assert result == "aaa"


def test_quint_paren():
    """5-level parentheses: (((((aaa)))))"""
    expr = "(((((aaa)))))"
    result = parse(expr)
    assert result == "aaa"
