import pytest
from pyparsing import ParseException

from utils.check_license import build_parser, eval_expr


@pytest.fixture(scope="module")
def parser():
    return build_parser()


def parse(expr):
    parser = build_parser()
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
