import pytest

from vsc.parser.parser import parse_valuascript
from vsc.parser.classes import *
from ..utils.factory_helpers import *
from vsc.exceptions import ValuaScriptError, ErrorCode

# This file aims at testing explicitly the right side of an assignment
# in the test_parse_assignments.py file tests where minimal and focused on the left side
# here the left side will be minimal and we will test that the expressions are passed correctly.
# Note that in the said file we implicitly already tested all the atom "rules" and
# all comparison expressions.
# This file will then focus on:

# 1) conditional expressions -> "ce" -> pytest id
# in Lark file conditional_expression: or_expression | IF or_expression THEN or_expression ELSE conditional_expression
# this means that being it declared before all others it can contain them
# both as <condition> (i.e. the part after if)
# and as <then> block
# the <else> block can be a recursive <conditional expression>
# that said in this file we will test only the nested conditional
# as the other parts are tested in isolation and
# it is Lark responsibility to handle that

# 2) or/and/not expressions -> "be" -> (boolean expression) -> pytest id
# We explicitly test precedence override and chaining

# 3) comparison expressions -> "ce" -> pytest id
# We explicitly test for sad path only as the happy one is already covered

# 4) math expressions -> "me" -> pytest id
# We explicitly test for all operators and nesting

# 5) Specific atom rules like float and separators -> "at" -> pytest id

@pytest.mark.parametrize(
    "code",
    [
    pytest.param("let a = if true then 10 else if false then 14 else 11", id="ce_nested_in_else_branch"),
    pytest.param("let a = not(x and (y or z)) and not z and y", id="be_nested"),
    pytest.param("let a = x + y", id="me_+"),
    pytest.param("let a = x - y", id="me_-"),
    pytest.param("let a = x * y", id="me_*"),
    pytest.param("let a = x / y", id="me_/"),
    pytest.param("let a = x^y", id="me_^"),
    pytest.param("let a = ((x + y) / (12 + 2))^12", id="me_precedence_and_nesting"),
    pytest.param("let a = 1_000", id="at_separator"),
    pytest.param("let a = 1.3242", id="at_float"),
    pytest.param("let a = 1_103.3_242", id="at_float_and_separator"),
    pytest.param("let a = +1_103.3_242", id="at_float_and_separator_signed_1"),
    pytest.param("let a = -1_103.3_242", id="at_float_and_separator_signed_2"),
    ]
)
def test_expression_parsed_correctly(code):
    """Tests that all assignments types are parsed correctly."""
    ast = parse_valuascript(code)
    assert ast is not None



@pytest.mark.parametrize(
    "code, error",
    [
    pytest.param("let a = true then 10 else 11", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_missing_if"),
    pytest.param("let a = if true 10 else 11", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_missing_then"),
    pytest.param("let a = if true then 10 11", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_missing_else"),
    pytest.param("let a = if then 10 else 11", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_missing_condition"),
    pytest.param("let a = if true then else 11", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_missing_then_value"),
    pytest.param("let a = if true then 10 else", ErrorCode.SYNTAX_PARSING_ERROR, id="ce_missing_else_value"),
    pytest.param("let a = if x then if y then 1 else 2", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_dangling_else_binds_to_inner_if"),

    pytest.param("let a = x an y", ErrorCode.SYNTAX_INVALID_CHARACTER, id="be_wrong_identifier_1"),
    pytest.param("let a = x o y", ErrorCode.SYNTAX_INVALID_CHARACTER, id="be_wrong_identifier_2"),
    pytest.param("let a = no true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="be_wrong_identifier_3"),

    pytest.param("let a = x === y", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_wrong_identifier_1"),
    pytest.param("let a = x !== y", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_wrong_identifier_2"),
    pytest.param("let a = >== true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_wrong_identifier_3"),
    pytest.param("let a = <== true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_wrong_identifier_4"),
    pytest.param("let a = >=== true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_wrong_identifier_5"),
    pytest.param("let a = <=== true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="ce_wrong_identifier_6"),

    pytest.param("let a = x ++ y", ErrorCode.SYNTAX_INVALID_CHARACTER, id="me_wrong_identifier_1"),
    pytest.param("let a = x -- y", ErrorCode.SYNTAX_INVALID_CHARACTER, id="me_wrong_identifier_2"),
    pytest.param("let a = ** true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="me_wrong_identifier_3"),
    pytest.param("let a = // true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="me_wrong_identifier_4"),
    pytest.param("let a = ^^ true", ErrorCode.SYNTAX_INVALID_CHARACTER, id="me_wrong_identifier_5"),

    pytest.param("let a = 1.", ErrorCode.SYNTAX_INVALID_CHARACTER, id="at_wrong_identifier_1"),
    pytest.param("let a = .5", ErrorCode.SYNTAX_INVALID_CHARACTER, id="at_wrong_identifier_2"),
    pytest.param("let a = 1_", ErrorCode.SYNTAX_INVALID_CHARACTER, id="at_wrong_identifier_3"),
    pytest.param("let a = 1__000", ErrorCode.SYNTAX_INVALID_CHARACTER, id="at_double_underscore_invalid"),
    ]
)
def test_expression_parsed_error(code, error):
    with pytest.raises(ValuaScriptError) as excinfo:
        parse_valuascript(code)

    # Check that the raised exception has the correct custom error code
    assert excinfo.value.code == error
   
