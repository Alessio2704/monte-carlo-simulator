import pytest

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import *
from vsc.parser.core.parser import parse_valuascript


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("let a = 1000", id="number"),
        pytest.param('let a = "string"', id="string"),
        pytest.param("let a = [1,2,3]", id="vector literal"),
        pytest.param("let a = true", id="boolean"),
        pytest.param("let _a = false", id="cname_1"),
        pytest.param("let ifthenelse = 1", id="identifier_containing_keyword"),
        pytest.param("let a = some_func()", id="function_call"),
        pytest.param("let a, b = some_func()", id="multi_assignment"),
        pytest.param("let a = if true then 10 else 4", id="conditional_expression"),
        pytest.param("let a = x or y", id="or"),
        pytest.param("let a = x and y", id="and"),
        pytest.param("let a = not x", id="not"),
        pytest.param("let a = x == y", id="=="),
        pytest.param("let a = x != y", id="!="),
        pytest.param("let a = x > y", id=">"),
        pytest.param("let a = x < y", id="<"),
        pytest.param("let a = x >= y", id=">="),
        pytest.param("let a = x <= y", id="<="),
        pytest.param("let a = x^y", id="pow"),
        pytest.param("let a = x[1]", id="access_vector_element"),
        pytest.param("let a = x[:1]", id="delete_vector_element"),
        pytest.param("let a = (x + y) * z", id="parenthesis_in_assignment"),
    ],
)
def test_assignment_parsed_correctly(code):
    """Tests that all assignments types are parsed correctly."""
    ast = parse_valuascript(code)
    assert ast is not None


@pytest.mark.parametrize(
    "code, error",
    [
        pytest.param("let x = ", ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS, id="missing_value_after_="),
        pytest.param("x = 1", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_let"),
        pytest.param("let = 1", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_var_name"),
        pytest.param("let 12 = 1", ErrorCode.SYNTAX_INVALID_IDENTIFIER, id="invalid_cname_for_var_name_1"),
        pytest.param("let -var = 1", ErrorCode.SYNTAX_INVALID_IDENTIFIER, id="invalid_cname_for_var_name_2"),
        pytest.param(
            "let x, = some_func()",
            ErrorCode.SYNTAX_INVALID_CHARACTER,
            id="missing_multi_assignment_second_var",
        ),
        pytest.param(
            "let x y = some_func()",
            ErrorCode.SYNTAX_INVALID_IDENTIFIER,
            id="missing_multi_assignment_comma",
        ),
        pytest.param(
            "let x, y = ",
            ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS,
            id="missing_value_after_=_multi_assignment",
        ),
        pytest.param(
            "x, y = some_func()",
            ErrorCode.SYNTAX_INVALID_CHARACTER,
            id="missing_let_multi_assignment",
        ),
        pytest.param(
            "let x = a > b > c",
            ErrorCode.SYNTAX_INVALID_CHARACTER,
            id="chaining_not_allowed_for_comparison",
        ),
    ],
)
def test_assignment_parsed_error(code, error):
    with pytest.raises(ValuaScriptError) as excinfo:
        parse_valuascript(code)

    # Check that the raised exception has the correct custom error code
    assert excinfo.value.code == error
