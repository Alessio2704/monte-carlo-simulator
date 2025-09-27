import pytest

from vsc.parser.parser import parse_valuascript
from vsc.parser.classes import *
from ..utils.factory_helpers import *
from ..utils.assertion_helper import assert_asts_equal

@pytest.mark.parametrize(
    "code, expected_directive",
    [
    pytest.param("@iterations = 1000", get_directive(name="iterations", value=get_number_literal(1000)), id="iterations"),
    pytest.param("@output = my_var", get_directive(name="output", value=get_identifier("my_var")), id="output"), 
    pytest.param('@output_file = "results.csv"', get_directive(name="output_file", value= get_string_literal("results.csv")), id="output_file"),
    pytest.param("@module", get_directive(name="module", value=get_boolean_literal(True)), id="module"),
    ]
)
def test_directive_parsed_correctly(code, expected_directive):
    """Tests that all directive types are parsed correctly."""
    ast = parse_valuascript(code)
    assert isinstance(ast, Root)
    assert len(ast.directives) == 1

    actual_directive = ast.directives[0]
    assert_asts_equal(actual_directive, expected_directive)

@pytest.mark.parametrize(
    "code, expected_import",
    [
    pytest.param('@import "my/file/path"', get_import("my/file/path"), id="import")
    ]
)
def test_import_parsed_correctly(code, expected_import):
    """Tests that all directive types are parsed correctly."""
    ast = parse_valuascript(code)
    assert isinstance(ast, Root)
    assert len(ast.imports) == 1

    actual_import = ast.imports[0]
    assert_asts_equal(actual_import, expected_import)

        