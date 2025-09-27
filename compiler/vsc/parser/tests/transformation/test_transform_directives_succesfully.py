import pytest

from vsc.parser.parser import parse_valuascript
from vsc.parser.classes import *
from ..utils.factory_helpers import *

@pytest.mark.parametrize(
    "code, name, value",
    [
    ("@iterations = 1000", "iterations", get_number_literal(1000)),
    ("@output = my_var", "output", get_identifier("my_var")), 
    ('@output_file = "results.csv"', "output_file", get_string_literal("results.csv")),
    ("@module", "module", get_boolean_literal(True))
    ]
)
def test_directive_parsed_correctly(code, name, value):
    """Tests that all directive types are parsed correctly."""
    ast = parse_valuascript(code)
    assert isinstance(ast, Root)
    assert len(ast.directives) == 1

    directive = ast.directives[0]
    assert directive.name == name
    assert directive.value.value == value.value

def test_import_directive_parsed_correctly():
    code = '@import "my_module.vs"'
    ast = parse_valuascript(code)
    assert isinstance(ast, Root)
    assert len(ast.imports) == 1
    import_dir = ast.imports[0]
    assert import_dir.path == "my_module.vs"