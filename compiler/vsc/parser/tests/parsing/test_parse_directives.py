import pytest

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import *
from vsc.parser.core.parser import parse_valuascript


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("@iterations = 1000", id="iterations"),
        pytest.param("@output = my_var", id="output"),
        pytest.param('@output_file = "results.csv"', id="output_file"),
        pytest.param("@module", id="module"),
    ],
)
def test_directive_parsed_correctly(code):
    """Tests that all directive types are parsed correctly."""
    ast = parse_valuascript(code)
    assert ast is not None


@pytest.mark.parametrize(
    "code, error",
    [
        pytest.param("iterations = 1000", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_@"),
        pytest.param("*iterations = 1000", ErrorCode.SYNTAX_INVALID_CHARACTER, id="other_from_@"),
        pytest.param("@ = 1000", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_after_name_@"),
        pytest.param("@iterations 1000", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_="),
        pytest.param(
            "@iterations = ",
            ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS,
            id="missing_value_after_=",
        ),
        pytest.param("module", ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_@_valueless_directive"),
        pytest.param("*module", ErrorCode.SYNTAX_INVALID_CHARACTER, id="other_from_@_valueless_directive"),
        pytest.param("@", ErrorCode.SYNTAX_PARSING_ERROR, id="missing_after_name_@_valueless_directive"),
        pytest.param('@ "path"', ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_import_keyword"),
        pytest.param('"path"', ErrorCode.SYNTAX_INVALID_CHARACTER, id="missing_import_directive"),
    ],
)
def test_directive_parsed_error(code, error):
    with pytest.raises(ValuaScriptError) as excinfo:
        parse_valuascript(code)

    # Check that the raised exception has the correct custom error code
    assert excinfo.value.code == error
