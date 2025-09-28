import pytest

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import *
from vsc.parser.core.parser import parse_valuascript


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("func test() -> scalar { return 1 }", id="basic"),
        pytest.param("func test(a: scalar) -> scalar { return 1 }", id="1_param"),
        pytest.param("func test(a: scalar, a: scalar, a: scalar) -> scalar { return 1 }", id="3_param"),
        pytest.param("func test() -> (scalar, vector, boolean) { return 1 }", id="returns_3_tuple"),
        pytest.param("func test() -> (scalar) { return Normal(1, 2) }", id="basic_returns_function"),
        pytest.param("func test() -> (scalar) { return (Normal(1, 2) * Pert(1,2))^2 }", id="basic_returns_complex_inline"),
        pytest.param('func test() -> (scalar) { """Docstring here""" \n return 1 }', id="basic_docstring"),
        pytest.param("func test() -> (scalar) { let a = 10 \n let b = some_func() \n let c = a + b \n return c }", id="assignment_body"),
        pytest.param("func weird_comment(a: # comment here\nscalar) -> scalar { return a }", id="comment_inside_parameters"),
        pytest.param("let x = 1 # comment\n + 2", id="comment_breaking_expression_across_lines"),
    ],
)
def test_function_definition_parsed_correctly(code):
    """Tests that all assignments types are parsed correctly."""
    ast = parse_valuascript(code)
    assert ast is not None


@pytest.mark.parametrize(
    "code, error",
    [
        pytest.param("test() -> scalar { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_func"),
        pytest.param("test( -> scalar { return 1 }", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_)"),
        pytest.param("test) -> scalar { return 1 }", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_("),
        pytest.param("func test -> scalar { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_()"),
        pytest.param("func test() scalar { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_(->)"),
        pytest.param("func test() -> { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_return_type"),
        pytest.param("func test() { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_return_type_annotation"),
        pytest.param("func test() - { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="invalid_(->)_1"),
        pytest.param("func test() > { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="invalid_(->)_2"),
        pytest.param("func test() -> scalar  { return 1", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_}"),
        pytest.param("func test() -> scalar  return 1 }", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_{"),
        pytest.param("func test() -> scalar return 1 ", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_curly_brackets"),
        pytest.param("func test() -> scalar { return }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_return_value"),
        pytest.param("func test() -> scalar { 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_return_keyword"),
        pytest.param('func test() -> scalar {"" return 1 }', ErrorCode.SYNTAX_INVALID_CHARACTER, id="invalid_docstring"),
        pytest.param('func test() -> scalar {""""" return 1 }', ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_docstring_closing"),
        pytest.param("func test(a) -> scalar { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_param_type"),
        pytest.param("func test(:scalar) -> scalar { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_param_name"),
        pytest.param("func test(a:) -> scalar { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_param_type"),
        pytest.param("func test() -> (scalar, ) { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="unterminated_tuple_return_type"),
        pytest.param("func test() -> scalar, scalar { return 1 }", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_tuple_parenthesis"),
        pytest.param("func test() -> scalar, scalar) { return 1 }", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_parenthesis_in_return_type_1"),
        pytest.param("func test() -> (scalar, scalar", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_parenthesis_in_return_type_2"),
        pytest.param("func empty() -> scalar {}", ErrorCode.SYNTAX_INVALID_CHARACTER, id="empty_function_body"),
    ],
)
def test_function_definition_parsed_error(code, error):
    with pytest.raises(ValuaScriptError) as excinfo:
        parse_valuascript(code)

    # Check that the raised exception has the correct custom error code
    assert excinfo.value.code == error
