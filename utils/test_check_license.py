import pytest
from pyparsing import ParseException

from utils.check_license import build_parser, eval_expr


@pytest.fixture(scope="module")
def allowed_set():
    return {
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
    }


@pytest.fixture(scope="module")
def parser(allowed_set):
    return build_parser(allowed_set)


def parse(expr, _allowed_set=None):
    parser = build_parser(_allowed_set or {
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
    })
    return parser.parseString(expr, parseAll=True)


# --- Parsing Tests ---


def test_simple_license_name(parser):
    result = parser.parseString("Apache-2.0", parseAll=True).asList()
    assert result == ["Apache-2.0"]


def test_parenthesis_annotation(parser):
    """Annotation parentheses (MPL 2.0) are not treated as logical parentheses"""
    result = parser.parseString(
        "Mozilla Public License 2.0 (MPL 2.0)", parseAll=True
    ).asList()
    assert result == ["Mozilla Public License 2.0 (MPL 2.0)"]


def test_simple_and_expression(parser):
    result = parser.parseString("Apache-2.0 AND MIT", parseAll=True).asList()
    assert result == [["Apache-2.0", "AND", "MIT"]]


def test_simple_or_expression(parser):
    result = parser.parseString("BSD-3-Clause OR MIT", parseAll=True).asList()
    assert result == [["BSD-3-Clause", "OR", "MIT"]]


def test_expression_with_parentheses(parser):
    result = parser.parseString(
        "(Apache-2.0 OR MIT) AND BSD-3-Clause", parseAll=True
    ).asList()
    # infixNotation returns a nested list structure
    assert result == [[["Apache-2.0", "OR", "MIT"], "AND", "BSD-3-Clause"]]


def test_nested_parentheses(parser):
    """Nested structure is processed correctly"""
    result = parser.parseString(
        "(Apache-2.0 AND (MIT OR BSD-3-Clause))", parseAll=True
    ).asList()
    assert result == [[["Apache-2.0", "AND", ["MIT", "OR", "BSD-3-Clause"]]]]


def test_consecutive_operators(parser):
    """Syntax error for consecutive AND/OR"""
    with pytest.raises(ParseException):
        parser.parseString("Apache-2.0 AND OR MIT", parseAll=True)


def test_slash_as_and(parser):
    """Treat slash delimiter as AND"""
    result = parser.parseString("Apache-2.0 / MIT", parseAll=True).asList()
    assert result == [["Apache-2.0", "AND", "MIT"]]


def test_semicolon_as_and(parser):
    """Treat semicolon delimiter as AND"""
    result = parser.parseString("MIT; BSD-3-Clause", parseAll=True).asList()
    assert result == [["MIT", "AND", "BSD-3-Clause"]]


def test_annotation_not_confused_with_logic(parser):
    """Do not treat as logical expression if AND is not inside parentheses"""
    expr = "MIT License (X11 Style)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT License (X11 Style)"]


def test_annotation_with_logic_inside(parser):
    """Treat as logical parentheses if AND/OR are inside parentheses"""
    expr = "MIT AND (Apache-2.0 OR BSD-3-Clause)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["MIT", "AND", ["Apache-2.0", "OR", "BSD-3-Clause"]]]


# --- Evaluation Tests ---


def test_eval_simple_true():
    parsed = parse("Apache-2.0")[0]
    assert eval_expr(parsed, {"apache-2.0"}) is True


def test_eval_simple_false():
    parsed = parse("MIT")[0]
    assert eval_expr(parsed, {"apache-2.0"}) is False


def test_eval_and_expression():
    parsed = parse("Apache-2.0 AND MIT")[0]
    assert eval_expr(parsed, {"apache-2.0", "mit"}) is True
    assert eval_expr(parsed, {"apache-2.0"}) is False


def test_eval_or_expression():
    parsed = parse("Apache-2.0 OR MIT")[0]
    assert eval_expr(parsed, {"apache-2.0"}) is True
    assert eval_expr(parsed, {"mit"}) is True
    assert eval_expr(parsed, {"bsd-3-clause"}) is False


def test_eval_nested_expression():
    parsed = parse("(Apache-2.0 OR MIT) AND BSD-3-Clause")[0]
    assert eval_expr(parsed, {"apache-2.0", "bsd-3-clause"}) is True
    assert eval_expr(parsed, {"mit", "bsd-3-clause"}) is True
    assert eval_expr(parsed, {"apache-2.0"}) is False


def test_eval_with_case_insensitivity():
    parsed = parse("APACHE-2.0 or mit")[0]
    assert eval_expr(parsed, {"apache-2.0"}) is True
    assert eval_expr(parsed, {"mit"}) is True
    assert eval_expr(parsed, {"bsd"}) is False


def test_eval_with_slash_and_semicolon():
    parsed1 = parse("MIT / BSD-3-Clause")[0]
    parsed2 = parse("MIT; BSD-3-Clause")[0]
    assert eval_expr(parsed1, {"mit", "bsd-3-clause"}) is True
    assert eval_expr(parsed2, {"mit"}) is False


def test_eval_nested_and_or_mixed():
    """Complex expression like (A OR B) AND (C OR D)"""
    expr = "(Apache-2.0 OR MIT) AND (BSD-3-Clause OR Unlicense)"
    parsed = parse(expr)[0]
    assert eval_expr(parsed, {"apache-2.0", "bsd-3-clause"}) is True
    assert eval_expr(parsed, {"mit", "unlicense"}) is True
    assert eval_expr(parsed, {"apache-2.0"}) is False


# --- Additional Tests (More Complex and Diverse Inputs) ---


def test_long_chained_expression(parser):
    """Expression with many chained AND/OR"""
    expr = "Apache-2.0 OR MIT AND BSD-3-Clause OR Unlicense AND Zlib"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["Apache-2.0", "OR", ["MIT", "AND", "BSD-3-Clause"]],
            "OR",
            ["Unlicense", "AND", "Zlib"],
        ]
    ]


def test_multiple_levels_of_annotations(parser):
    """Case where annotation exists at multiple levels"""
    expr = "MIT License (Expat (2010 Revision))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT License (Expat (2010 Revision))"]


def test_mixed_logic_and_annotations(parser):
    """Complex logical expression including annotations"""
    expr = "(Apache-2.0 (SPDX)) AND (BSD-3-Clause OR MIT (X11))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            "Apache-2.0 (SPDX)",
            "AND",
            ["BSD-3-Clause", "OR", "MIT (X11)"],
        ]
    ]


def test_annotation_with_special_chars(parser):
    """Annotation containing special characters like dots or hyphens"""
    expr = "BSD-3-Clause (version-2.0.alpha)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["BSD-3-Clause (version-2.0.alpha)"]


def test_parentheses_with_extra_spaces(parser):
    """Correct behavior even with extra spaces around parentheses"""
    expr = "(  Apache-2.0  OR  MIT  )  AND  BSD-3-Clause"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [[["Apache-2.0", "OR", "MIT"], "AND", "BSD-3-Clause"]]


def test_nested_and_or_with_annotation(parser):
    """Annotation license included in nested structure"""
    expr = "((MIT (X11)) OR (BSD-3-Clause AND Apache-2.0))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["MIT (X11)", "OR", ["BSD-3-Clause", "AND", "Apache-2.0"]],
        ]
    ]


def test_double_parentheses_pairs(parser):
    """Double parentheses structure"""
    expr = "((Apache-2.0))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Apache-2.0"]


def test_or_with_slash_and_semicolon(parser):
    """OR expression mixed with slash and semicolon"""
    expr = "(MIT / BSD-3-Clause) OR Apache-2.0; Zlib"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["MIT", "AND", "BSD-3-Clause"],
            "OR",
            ["Apache-2.0", "AND", "Zlib"],
        ]
    ]


def test_annotation_that_looks_like_operator(parser):
    """Do not misidentify words like 'AND' or 'OR' inside annotation"""
    expr = "MIT (compatible with OR later)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT (compatible with OR later)"]


def test_weird_but_valid_spacing(parser):
    """Irregular whitespace like spaces and newlines"""
    expr = "Apache-2.0  AND  \n  (MIT  OR  BSD-3-Clause)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Apache-2.0", "AND", ["MIT", "OR", "BSD-3-Clause"]]]


def test_multiple_license_blocks(parser):
    """Multiple blocks linked by logical OR"""
    expr = "(Apache-2.0 AND MIT) OR (BSD-3-Clause AND Zlib)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["Apache-2.0", "AND", "MIT"],
            "OR",
            ["BSD-3-Clause", "AND", "Zlib"],
        ]
    ]


def test_complex_annotation_and_or_mix(parser):
    """Complex mix of annotation and logical expression"""
    expr = "(Apache-2.0 (spdx)) AND ((MIT (X11)) OR BSD-3-Clause (3-Clause))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            "Apache-2.0 (spdx)",
            "AND",
            [["MIT (X11)", "OR", "BSD-3-Clause (3-Clause)"]],
        ]
    ]


def test_consecutive_and(parser):
    """Syntax error for consecutive AND"""
    with pytest.raises(ParseException):
        parser.parseString("MIT AND AND BSD-3-Clause", parseAll=True)


def test_consecutive_or(parser):
    """Syntax error for consecutive OR"""
    with pytest.raises(ParseException):
        parser.parseString("Apache-2.0 OR OR MIT", parseAll=True)


def test_extra_parentheses_pairs(parser):
    """Balanced extra parentheses are OK"""
    expr = "(((MIT)))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT"]


def test_invalid_token_is_treated_as_error(parser):
    """Invalid tokens like #invalid are treated as syntax errors"""
    expr = "#invalid"
    with pytest.raises(ParseException):
        parser.parseString(expr, parseAll=True)


def test_empty_parentheses_treated_as_annotation(parser):
    """Empty parentheses '()' are treated as an empty annotation"""
    expr = "MIT ()"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT ()"]


def test_double_nested_and_or(parser):
    """Multi-level nesting like (A AND (B OR (C AND D)))"""
    expr = "(Apache-2.0 AND (MIT OR (BSD-3-Clause AND Unlicense)))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            "Apache-2.0",
            "AND",
            ["MIT", "OR", ["BSD-3-Clause", "AND", "Unlicense"]],
        ]
    ]


def test_unbalanced_right_parenthesis(parser):
    """Syntax error for extra right parenthesis"""
    with pytest.raises(ParseException):
        parser.parseString("Apache-2.0 OR MIT)", parseAll=True)


def test_unbalanced_left_parenthesis(parser):
    """Syntax error for extra left parenthesis"""
    with pytest.raises(ParseException):
        parser.parseString("(Apache-2.0 OR MIT", parseAll=True)


def test_long_mixed_chain(parser):
    """Long mixed expression: AND/OR/comma/semicolon mix"""
    expr = "MIT, Apache-2.0; BSD-3-Clause OR Unlicense / Zlib"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["MIT", "AND", "Apache-2.0", "AND", "BSD-3-Clause"],
            "OR",
            ["Unlicense", "AND", "Zlib"],
        ]
    ]


# --- Additional Tests (Handling of Spaces, Annotations, and Multi-Word Licenses) ---


def test_license_with_spaces(parser):
    """License name containing spaces (e.g., Apache Software License)"""
    expr = "Apache Software License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Apache Software License"]


def test_license_with_spaces_and_and(parser):
    """AND expression between license names containing spaces"""
    expr = "Apache Software License AND MIT License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Apache Software License", "AND", "MIT License"]]


def test_license_with_version_and_annotation(parser):
    """Annotation name (e.g., Mozilla Public License 2.0 (MPL 2.0))"""
    expr = "Mozilla Public License 2.0 (MPL 2.0)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Mozilla Public License 2.0 (MPL 2.0)"]


def test_license_with_or_later_text(parser):
    """Long license name including 'or later' (e.g., LGPL v2.1 or later)"""
    expr = "GNU Lesser General Public License v2.1 or later"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["GNU Lesser General Public License v2.1 or later"]


def test_license_with_and_inside_name(parser):
    """'and' inside the license name is not misidentified as logical AND"""
    expr = "Research and Development License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Research and Development License"]


def test_license_with_parenthetical_long_annotation(parser):
    """Annotation including multiple words inside parentheses"""
    expr = "BSD License (3-Clause Clear License)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["BSD License (3-Clause Clear License)"]


def test_license_with_leading_article(parser):
    """License name including an article (The Unlicense)"""
    expr = "The Unlicense"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["The Unlicense"]


def test_license_with_dash_and_space_mix(parser):
    """Name mixing dashes and spaces (BSD 3-Clause)"""
    expr = "BSD 3-Clause"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["BSD 3-Clause"]


def test_license_with_annotation_and_logic(parser):
    """Logical expression including an annotated name"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) OR Apache-2.0"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Mozilla Public License 2.0 (MPL 2.0)", "OR", "Apache-2.0"]]


def test_license_with_spaces_and_parentheses_nested(parser):
    """Mix of spaces, annotations, and logical parentheses"""
    expr = "(Apache Software License OR Mozilla Public License 2.0 (MPL 2.0)) AND BSD-3-Clause"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["Apache Software License", "OR", "Mozilla Public License 2.0 (MPL 2.0)"],
            "AND",
            "BSD-3-Clause",
        ]
    ]


def test_simple_or_between_two_licenses(parser):
    """Simple OR expression (MIT or Apache-2.0)"""
    expr = "MIT or Apache-2.0"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["MIT", "OR", "Apache-2.0"]]


def test_simple_and_between_two_licenses(parser):
    """Simple AND expression (GPL and LGPL)"""
    expr = "GPL and LGPL"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["GPL", "AND", "LGPL"]]


# --- Complex Logical Expression Tests with Lowercase and/or ---


def test_lowercase_or_and_and_combination(parser):
    """Complex expression mixing lowercase or/and"""
    expr = "MIT and Apache-2.0 or BSD-3-Clause and Unlicense"
    result = parser.parseString(expr, parseAll=True).asList()
    # 'and' has higher precedence in infixNotation
    assert result == [
        [
            ["MIT", "AND", "Apache-2.0"],
            "OR",
            ["BSD-3-Clause", "AND", "Unlicense"],
        ]
    ]


def test_parenthesized_lowercase_logic(parser):
    """Expression using lowercase and/or with parentheses"""
    expr = "(mit or apache-2.0) and (bsd-3-clause or unlicense)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["mit", "OR", "apache-2.0"],
            "AND",
            ["bsd-3-clause", "OR", "unlicense"],
        ]
    ]


def test_nested_lowercase_logic(parser):
    """Nested lowercase and/or expression"""
    expr = "((mit or apache-2.0) and bsd-3-clause) or unlicense"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            [["mit", "OR", "apache-2.0"], "AND", "bsd-3-clause"],
            "OR",
            "unlicense",
        ]
    ]


def test_mixed_case_logic_expression(parser):
    """Composite expression with mixed case logic"""
    expr = "MIT or Apache-2.0 AND bsd-3-clause Or unlicense And Zlib"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["MIT", "OR", ["Apache-2.0", "AND", "bsd-3-clause"]],
            "OR",
            ["unlicense", "AND", "Zlib"],
        ]
    ]


# --- Lowercase and/or + Multi-Word License with Spaces or Annotation Tests ---


def test_lowercase_and_with_multiword_license(parser):
    """Connecting multi-word license names with 'and'"""
    expr = "Apache Software License and MIT License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Apache Software License", "AND", "MIT License"]]


def test_lowercase_or_with_multiword_license(parser):
    """Connecting multi-word license names with 'or'"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) or Apache Software License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        ["Mozilla Public License 2.0 (MPL 2.0)", "OR", "Apache Software License"]
    ]


def test_lowercase_and_or_mixed_with_multiword(parser):
    """Mixed lowercase and/or expression including multi-word licenses"""
    expr = "Apache Software License or MIT License and BSD License"
    result = parser.parseString(expr, parseAll=True).asList()
    # 'and' has higher precedence
    assert result == [
        [
            "Apache Software License",
            "OR",
            ["MIT License", "AND", "BSD License"],
        ]
    ]


def test_parenthesized_lowercase_and_or_with_multiword(parser):
    """Lowercase and/or expression combining parentheses and multi-word licenses"""
    expr = "(Apache Software License or MIT License) and (BSD License or Mozilla Public License 2.0 (MPL 2.0))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["Apache Software License", "OR", "MIT License"],
            "AND",
            ["BSD License", "OR", "Mozilla Public License 2.0 (MPL 2.0)"],
        ]
    ]

def test_complex_expression_with_and_inside_name_left(parser):
    """License name containing 'and' appears on the left side"""
    expr = "Research and Development License OR MIT"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Research and Development License", "OR", "MIT"]]


def test_complex_expression_with_and_inside_name_middle(parser):
    """License name containing 'and' appears in the middle"""
    expr = "Apache-2.0 AND Research and Development License OR BSD-3-Clause"
    result = parser.parseString(expr, parseAll=True).asList()
    # AND has higher precedence
    assert result == [
        [
            ["Apache-2.0", "AND", "Research and Development License"],
            "OR",
            "BSD-3-Clause",
        ]
    ]


def test_complex_expression_with_and_inside_name_right(parser):
    """License name containing 'and' appears on the right side"""
    expr = "MIT OR Research and Development License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["MIT", "OR", "Research and Development License"]]


def test_parenthesized_and_inside_name(parser):
    """License name containing 'and' appears within parentheses"""
    expr = "(Apache-2.0 OR Research and Development License) AND BSD-3-Clause"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["Apache-2.0", "OR", "Research and Development License"],
            "AND",
            "BSD-3-Clause",
        ]
    ]


def test_double_nested_and_inside_name(parser):
    """License name containing 'and' appears within multi-level nesting"""
    expr = "(MIT OR (BSD-3-Clause AND Research and Development License))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            "MIT",
            "OR",
            ["BSD-3-Clause", "AND", "Research and Development License"],
        ]
    ]

def test_research_and_dev_with_apache_left(parser):
    """Research and Development License on the left, combined with Apache Software License"""
    expr = "Research and Development License OR Apache Software License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Research and Development License", "OR", "Apache Software License"]]


def test_research_and_dev_with_apache_right(parser):
    """Research and Development License on the right, combined with Apache Software License"""
    expr = "Apache Software License AND Research and Development License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Apache Software License", "AND", "Research and Development License"]]


def test_research_and_dev_with_mozilla_left(parser):
    """Research and Development License on the left, combined with Mozilla Public License 2.0 (MPL 2.0)"""
    expr = "Research and Development License OR Mozilla Public License 2.0 (MPL 2.0)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Research and Development License", "OR", "Mozilla Public License 2.0 (MPL 2.0)"]]


def test_research_and_dev_with_mozilla_right(parser):
    """Research and Development License on the right, combined with Mozilla Public License 2.0 (MPL 2.0)"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) AND Research and Development License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Mozilla Public License 2.0 (MPL 2.0)", "AND", "Research and Development License"]]


def test_research_and_dev_nested_with_apache_and_mozilla(parser):
    """Multi-level nesting structure including Research and Development License (Apache + Mozilla combined)"""
    expr = "(Apache Software License OR (Mozilla Public License 2.0 (MPL 2.0) AND Research and Development License))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            "Apache Software License",
            "OR",
            ["Mozilla Public License 2.0 (MPL 2.0)", "AND", "Research and Development License"],
        ]
    ]


def test_research_and_dev_middle_with_mixed_complex(parser):
    """Research and Development License as an intermediate term in a complex logical expression"""
    expr = "Apache Software License AND Research and Development License OR Mozilla Public License 2.0 (MPL 2.0)"
    result = parser.parseString(expr, parseAll=True).asList()
    # AND takes precedence over OR
    assert result == [
        [
            ["Apache Software License", "AND", "Research and Development License"],
            "OR",
            "Mozilla Public License 2.0 (MPL 2.0)",
        ]
    ]


def test_research_and_dev_parenthesized(parser):
    """Logical expression where Research and Development License is enclosed in parentheses"""
    expr = "(Research and Development License OR Apache Software License) AND Mozilla Public License 2.0 (MPL 2.0)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["Research and Development License", "OR", "Apache Software License"],
            "AND",
            "Mozilla Public License 2.0 (MPL 2.0)",
        ]
    ]
