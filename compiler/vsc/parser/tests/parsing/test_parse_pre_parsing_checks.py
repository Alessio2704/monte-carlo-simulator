import pytest

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import *
from vsc.parser.core.parser import parse_valuascript


@pytest.mark.parametrize(
    "code, error",
    [
        pytest.param("let x = ", ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS, id="missing_value_after_="),
        pytest.param("let", ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT, id="incomplete_assignment"),
        pytest.param("let x = (", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_bracket"),
        pytest.param("let x = )", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_bracket"),
        pytest.param("let x = [", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_bracket"),
        pytest.param("let x = ]", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_bracket"),
        pytest.param("let x = {", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_bracket"),
        pytest.param("let x = }", ErrorCode.SYNTAX_UNMATCHED_BRACKET, id="missing_bracket"),
        pytest.param("let -var = 1", ErrorCode.SYNTAX_INVALID_IDENTIFIER, id="invalid_cname"),
        pytest.param("let func = 1", ErrorCode.SYNTAX_RESERVED_KEYWORD_AS_IDENTIFIER, id="reserved_keyword_as_var_name"),
    ],
)
def test_pre_parsing_parsed_error(code, error):
    with pytest.raises(ValuaScriptError) as excinfo:
        parse_valuascript(code)

    # Check that the raised exception has the correct custom error code
    assert excinfo.value.code == error
