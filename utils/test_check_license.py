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


# --- パース系テスト ---


def test_simple_license_name(parser):
    result = parser.parseString("Apache-2.0", parseAll=True).asList()
    assert result == ["Apache-2.0"]


def test_parenthesis_annotation(parser):
    """注釈付き括弧 (MPL 2.0) が論理括弧として扱われない"""
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
    # infixNotation はネストしたリスト構造を返す
    assert result == [[["Apache-2.0", "OR", "MIT"], "AND", "BSD-3-Clause"]]


def test_nested_parentheses(parser):
    """ネスト構造が正しく処理できる"""
    result = parser.parseString(
        "(Apache-2.0 AND (MIT OR BSD-3-Clause))", parseAll=True
    ).asList()
    assert result == [[["Apache-2.0", "AND", ["MIT", "OR", "BSD-3-Clause"]]]]


def test_consecutive_operators(parser):
    """連続するAND/ORの構文エラー"""
    with pytest.raises(ParseException):
        parser.parseString("Apache-2.0 AND OR MIT", parseAll=True)


def test_slash_as_and(parser):
    """スラッシュ区切りをANDとみなす"""
    result = parser.parseString("Apache-2.0 / MIT", parseAll=True).asList()
    assert result == [["Apache-2.0", "AND", "MIT"]]


def test_semicolon_as_and(parser):
    """セミコロン区切りをANDとみなす"""
    result = parser.parseString("MIT; BSD-3-Clause", parseAll=True).asList()
    assert result == [["MIT", "AND", "BSD-3-Clause"]]


def test_annotation_not_confused_with_logic(parser):
    """括弧内にANDが含まれていなければ論理式とみなさない"""
    expr = "MIT License (X11 Style)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT License (X11 Style)"]


def test_annotation_with_logic_inside(parser):
    """括弧内にAND/ORがある場合は論理括弧とみなす"""
    expr = "MIT AND (Apache-2.0 OR BSD-3-Clause)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["MIT", "AND", ["Apache-2.0", "OR", "BSD-3-Clause"]]]


# --- 評価系テスト ---


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
    assert eval_expr(parsed, {"MIT"}) is True
    assert eval_expr(parsed, {"bsd"}) is False


def test_eval_with_slash_and_semicolon():
    parsed1 = parse("MIT / BSD-3-Clause")[0]
    parsed2 = parse("MIT; BSD-3-Clause")[0]
    assert eval_expr(parsed1, {"mit", "bsd-3-clause"}) is True
    assert eval_expr(parsed2, {"mit"}) is False


def test_eval_nested_and_or_mixed():
    """(A OR B) AND (C OR D) のような複雑な式"""
    expr = "(Apache-2.0 OR MIT) AND (BSD-3-Clause OR Unlicense)"
    parsed = parse(expr)[0]
    assert eval_expr(parsed, {"apache-2.0", "bsd-3-clause"}) is True
    assert eval_expr(parsed, {"mit", "unlicense"}) is True
    assert eval_expr(parsed, {"apache-2.0"}) is False


# --- 追加テスト（より複雑で多様な入力） ---


def test_long_chained_expression(parser):
    """AND/ORが多数連鎖した式"""
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
    """注釈が複数段階で存在するケース"""
    expr = "MIT License (Expat (2010 Revision))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT License (Expat (2010 Revision))"]


def test_mixed_logic_and_annotations(parser):
    """注釈を含む複雑な論理式"""
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
    """注釈内にドットやハイフンなどの特殊文字がある場合"""
    expr = "BSD-3-Clause (version-2.0.alpha)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["BSD-3-Clause (version-2.0.alpha)"]


def test_parentheses_with_extra_spaces(parser):
    """括弧周囲に余分なスペースがあっても正しく動作"""
    expr = "(  Apache-2.0  OR  MIT  )  AND  BSD-3-Clause"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [[["Apache-2.0", "OR", "MIT"], "AND", "BSD-3-Clause"]]


def test_nested_and_or_with_annotation(parser):
    """注釈付きライセンスがネスト構造に含まれる"""
    expr = "((MIT (X11)) OR (BSD-3-Clause AND Apache-2.0))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["MIT (X11)", "OR", ["BSD-3-Clause", "AND", "Apache-2.0"]],
        ]
    ]


def test_double_parentheses_pairs(parser):
    """二重括弧構造"""
    expr = "((Apache-2.0))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Apache-2.0"]


def test_or_with_slash_and_semicolon(parser):
    """OR式にスラッシュとセミコロンが混在"""
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
    """注釈内にAND/ORという単語が含まれても誤認しない"""
    expr = "MIT (compatible with OR later)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT (compatible with OR later)"]


def test_weird_but_valid_spacing(parser):
    """スペースや改行など不規則な空白"""
    expr = "Apache-2.0  AND  \n  (MIT  OR  BSD-3-Clause)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Apache-2.0", "AND", ["MIT", "OR", "BSD-3-Clause"]]]


def test_multiple_license_blocks(parser):
    """複数ブロックを論理ORで連結"""
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
    """注釈と論理式の複合混在"""
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
    """連続するANDの構文エラー"""
    with pytest.raises(ParseException):
        parser.parseString("MIT AND AND BSD-3-Clause", parseAll=True)


def test_consecutive_or(parser):
    """連続するORの構文エラー"""
    with pytest.raises(ParseException):
        parser.parseString("Apache-2.0 OR OR MIT", parseAll=True)


def test_extra_parentheses_pairs(parser):
    """余分な括弧があってもバランスしていればOK"""
    expr = "(((MIT)))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT"]


def test_invalid_token_is_treated_as_error(parser):
    """#invalid のような不正トークンは構文エラーとして扱う"""
    expr = "#invalid"
    with pytest.raises(ParseException):
        parser.parseString(expr, parseAll=True)


def test_empty_parentheses_treated_as_annotation(parser):
    """空の括弧 '()' は空注釈として扱う"""
    expr = "MIT ()"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["MIT ()"]


def test_double_nested_and_or(parser):
    """(A AND (B OR (C AND D)))のような多段ネスト"""
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
    """右括弧だけ余っている構文エラー"""
    with pytest.raises(ParseException):
        parser.parseString("Apache-2.0 OR MIT)", parseAll=True)


def test_unbalanced_left_parenthesis(parser):
    """左括弧だけ余っている構文エラー"""
    with pytest.raises(ParseException):
        parser.parseString("(Apache-2.0 OR MIT", parseAll=True)


def test_long_mixed_chain(parser):
    """長い混在式：AND/OR/カンマ/セミコロン混合"""
    expr = "MIT, Apache-2.0; BSD-3-Clause OR Unlicense / Zlib"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["MIT", "AND", "Apache-2.0", "AND", "BSD-3-Clause"],
            "OR",
            ["Unlicense", "AND", "Zlib"],
        ]
    ]


# --- 追加テスト（空白・注釈・複合名称ライセンスの扱い） ---


def test_license_with_spaces(parser):
    """空白を含むライセンス名（例: Apache Software License）"""
    expr = "Apache Software License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Apache Software License"]


def test_license_with_spaces_and_and(parser):
    """空白を含むライセンス名同士のAND式"""
    expr = "Apache Software License AND MIT License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Apache Software License", "AND", "MIT License"]]


def test_license_with_version_and_annotation(parser):
    """Mozilla Public License 2.0 (MPL 2.0) のような注釈付き名称"""
    expr = "Mozilla Public License 2.0 (MPL 2.0)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Mozilla Public License 2.0 (MPL 2.0)"]


def test_license_with_or_later_text(parser):
    """or later を含む長いライセンス名（例: LGPL v2.1 or later）"""
    expr = "GNU Lesser General Public License v2.1 or later"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["GNU Lesser General Public License v2.1 or later"]


def test_license_with_and_inside_name(parser):
    """ライセンス名中の 'and' は論理ANDと誤認されない"""
    expr = "Research and Development License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["Research and Development License"]


def test_license_with_parenthetical_long_annotation(parser):
    """括弧内に複数単語を含む注釈"""
    expr = "BSD License (3-Clause Clear License)"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["BSD License (3-Clause Clear License)"]


def test_license_with_leading_article(parser):
    """冠詞を含むライセンス名 (The Unlicense)"""
    expr = "The Unlicense"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["The Unlicense"]


def test_license_with_dash_and_space_mix(parser):
    """ダッシュと空白を混在させた名称 (BSD 3-Clause)"""
    expr = "BSD 3-Clause"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == ["BSD 3-Clause"]


def test_license_with_annotation_and_logic(parser):
    """注釈付き名称を含む論理式"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) OR Apache-2.0"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Mozilla Public License 2.0 (MPL 2.0)", "OR", "Apache-2.0"]]


def test_license_with_spaces_and_parentheses_nested(parser):
    """空白・注釈・論理括弧の混在"""
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
    """単純なOR式 (MIT or Apache-2.0)"""
    expr = "MIT or Apache-2.0"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["MIT", "OR", "Apache-2.0"]]


def test_simple_and_between_two_licenses(parser):
    """単純なAND式 (GPL and LGPL)"""
    expr = "GPL and LGPL"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["GPL", "AND", "LGPL"]]


# --- 小文字 and / or を使った複雑な論理式テスト ---


def test_lowercase_or_and_and_combination(parser):
    """小文字or/andを混在させた複雑な式"""
    expr = "MIT and Apache-2.0 or BSD-3-Clause and Unlicense"
    result = parser.parseString(expr, parseAll=True).asList()
    # infixNotationでは and の方が優先順位が高い
    assert result == [
        [
            ["MIT", "AND", "Apache-2.0"],
            "OR",
            ["BSD-3-Clause", "AND", "Unlicense"],
        ]
    ]


def test_parenthesized_lowercase_logic(parser):
    """括弧付きで小文字and/orを使った式"""
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
    """ネスト構造の小文字and/or式"""
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
    """大文字と小文字が混在した複合式"""
    expr = "MIT or Apache-2.0 AND bsd-3-clause Or unlicense And Zlib"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["MIT", "OR", ["Apache-2.0", "AND", "bsd-3-clause"]],
            "OR",
            ["unlicense", "AND", "Zlib"],
        ]
    ]


# --- 小文字 and/or + 空白や注釈を含む複合名称テスト ---


def test_lowercase_and_with_multiword_license(parser):
    """空白を含むライセンス名をandで接続"""
    expr = "Apache Software License and MIT License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [["Apache Software License", "AND", "MIT License"]]


def test_lowercase_or_with_multiword_license(parser):
    """空白を含むライセンス名をorで接続"""
    expr = "Mozilla Public License 2.0 (MPL 2.0) or Apache Software License"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        ["Mozilla Public License 2.0 (MPL 2.0)", "OR", "Apache Software License"]
    ]


def test_lowercase_and_or_mixed_with_multiword(parser):
    """複数語ライセンスを含む小文字and/or混在式"""
    expr = "Apache Software License or MIT License and BSD License"
    result = parser.parseString(expr, parseAll=True).asList()
    # and の方が優先順位が高い
    assert result == [
        [
            "Apache Software License",
            "OR",
            ["MIT License", "AND", "BSD License"],
        ]
    ]


def test_parenthesized_lowercase_and_or_with_multiword(parser):
    """括弧と複数語ライセンスを組み合わせた小文字and/or式"""
    expr = "(Apache Software License or MIT License) and (BSD License or Mozilla Public License 2.0 (MPL 2.0))"
    result = parser.parseString(expr, parseAll=True).asList()
    assert result == [
        [
            ["Apache Software License", "OR", "MIT License"],
            "AND",
            ["BSD License", "OR", "Mozilla Public License 2.0 (MPL 2.0)"],
        ]
    ]
