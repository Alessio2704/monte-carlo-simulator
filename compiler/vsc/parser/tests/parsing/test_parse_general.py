import pytest

from vsc.parser.core.classes import *
from vsc.parser.core.parser import parse_valuascript
from vsc.parser.utils.assertion_helper import *
from vsc.parser.utils.factory_helpers import *


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("", id="empty_file"),
        pytest.param("# comment", id="only_comment"),
        pytest.param("\t\t   ", id="tabs_and_spaces"),
    ],
)
def test_parsed_file_successfully(code):
    ast = parse_valuascript(code)
    assert ast is not None


def test_strange_order_declarations():
    code = "let a = 1 \n func b() -> scalar { return 2 } \n@directive = 3 \nlet c = 4"
    ast = parse_valuascript(code)
    assert ast is not None
    assert len(ast.directives) == 1
    assert len(ast.execution_steps) == 2
    assert len(ast.function_definitions) == 1

    a = get_literal_assignment(target="a", value=get_number_literal(1))
    b = get_function_def(name="b", params=[], return_type="scalar", body=[get_return_statement(get_number_literal(2))])
    c = get_literal_assignment(target="c", value=get_number_literal(4))
    directive = get_directive(name="directive", value=get_number_literal(3))

    assert_asts_equal(ast.execution_steps[0], a)
    assert_asts_equal(ast.function_definitions[0], b)
    assert_asts_equal(ast.directives[0], directive)
    assert_asts_equal(ast.execution_steps[1], c)
