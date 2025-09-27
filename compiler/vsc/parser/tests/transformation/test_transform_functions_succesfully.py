import pytest

from vsc.parser.parser import parse_valuascript
from vsc.parser.classes import *
from ..utils.factory_helpers import *
from ..utils.assertion_helper import assert_asts_equal

# Test basic simpler function
basic_func_code = "func my_func() -> scalar { return 1 }"
basic_func_expected =  get_function_def(
    name="my_func", 
    return_type="scalar",
    body=[get_return_statement(get_number_literal(1))]
    )

# Test spaces tabs and comments
space_tab_comments_code = "func my_func() -> scalar {#nfuybfbe \n \t \t \t \n return 1 }"
space_tab_comments_expected = get_function_def(
    name="my_func", 
    return_type="scalar",
    body=[get_return_statement(get_number_literal(1))]
    )

# Test return type
tuple_2_elems_code = "func my_func() -> (scalar, vector) { return 1 }"
tuple_2_elems_expected = get_function_def(
    name="my_func", 
    return_type=["scalar", "vector"], 
    body=[get_return_statement(get_number_literal(1))])

tuple_3_elems_code = "func my_func() -> (scalar, vector, boolean) { return 1 }"
tuple_3_elems_expected = get_function_def(
    name="my_func", 
    return_type=["scalar", "vector", "boolean"], 
    body=[get_return_statement(get_number_literal(1))])

# Test parameters
param_1_code = "func my_func(a: scalar) -> scalar { return 1 }"
param_1_expected = get_function_def(
    name="my_func",
    params=[('a', 'scalar')],
    return_type="scalar",
    body=[get_return_statement(get_number_literal(1))])

param_2_code = "func my_func(a: scalar, b: vector) -> scalar { return 1 }"
param_2_expected = get_function_def(
    name="my_func",
    params=[("a", "scalar"), ("b", "vector")],
    return_type="scalar",
    body=[get_return_statement(get_number_literal(1))])

param_3_code = "func my_func(a: scalar, b: vector, c: boolean) -> scalar { return 1 }"
param_3_expected = get_function_def(
    name="my_func",
    params=[("a", "scalar"), ("b", "vector"), ("c", "boolean")],
    return_type="scalar",
    body=[get_return_statement(get_number_literal(1))])

# Test docstring
docstring_code = "func my_func() -> scalar {\"\"\"Docstring test\"\"\" return 1 }"
docstring_expected = get_function_def(
    name="my_func", return_type="scalar",
    body=[get_return_statement(get_number_literal(1))], 
    docstring="Docstring test")

 # Test tuple return
tuple_simple_code = "func my_func() -> scalar { return (1, 2) }"
tuple_simple_expected = get_function_def(
    name="my_func", 
    return_type="scalar", 
    body=[
        get_return_statement(
            get_tuple_literal(items=[get_number_literal(1), get_number_literal(2)]))
        ]
)

tuple_sophisticated_body_code = "func my_func() -> scalar { let x = 10.45 \n let y = 12 return (x, y) }"
tuple_sophisticated_body_expected = get_function_def(
    name="my_func", 
    return_type="scalar",
    body=[
        get_literal_assignment(target="x", value=get_number_literal(10.45)),
        get_literal_assignment(target="y", value=get_number_literal(12)),
        get_return_statement(
            get_tuple_literal(items=[get_identifier("x"), get_identifier("y")])
            )
        ]
)


# Test body
body_assignment_code = "func my_func() -> scalar { let a = 10 \n return 1}"
body_assignment_expected = get_function_def(
    name="my_func", 
    return_type="scalar", 
    body=[
        get_literal_assignment(target="a", value=get_number_literal(10)),
        get_return_statement(get_number_literal(1))
    ]
)

body_assignment_and_return_code = "func my_func() -> scalar { let a = 10 \n return a}"
body_assignment_and_return_expected = get_function_def(
    name="my_func", 
    return_type="scalar", 
    body=[
        get_literal_assignment(target="a", value=get_number_literal(10)),
        get_return_statement(get_identifier("a"))
    ]
)

body_multi_assignment_code = "func my_func() -> scalar { let a, b = some_func() \n return a }"
body_multi_assignment_expected = get_function_def(
    name="my_func",
    return_type="scalar", 
    body=[
        get_multi_assignment(targets=[get_identifier("a"), get_identifier("b")], expression=get_function_call(function="some_func", args=[])),
        get_return_statement(get_identifier("a"))
    ]
)

body_complex_code_1 = "func my_func() -> scalar { let a = 10 \n let b = [1,2,3,4] \n let c = true \n let d = some_func() \n return a + b + c + d  }"
body_complex_expected_1 =  get_function_def(
    name="my_func",
    return_type="scalar",
    body=[
        get_literal_assignment(target="a", value=get_number_literal(10)),
        get_literal_assignment(target="b", value=get_vector_literal([get_number_literal(1), get_number_literal(2), get_number_literal(3), get_number_literal(4)])),
        get_literal_assignment(target="c", value=get_boolean_literal(True)),
        get_execution_assignment(target="d", expression=get_function_call(function="some_func", args=[])),
        get_return_statement(returns=get_function_call(
            function="add", 
            args=[get_identifier("a"), get_identifier("b"), get_identifier("c"), get_identifier("d")]))
    ]
)

body_complex_code_2 = "func my_func() -> (scalar, vector) { let a = 10 \n let b = [1,2,3,4] \n let c = true \n let d = some_func() \n return (a + b + c + d, b)  }"
body_complex_expected_2 =  get_function_def(
    name="my_func",
    return_type=["scalar", "vector"],
    body=[
        get_literal_assignment(target="a", value=get_number_literal(10)),
        get_literal_assignment(target="b", value=get_vector_literal([get_number_literal(1), get_number_literal(2), get_number_literal(3), get_number_literal(4)])),
        get_literal_assignment(target="c", value=get_boolean_literal(True)),
        get_execution_assignment(target="d", expression=get_function_call(function="some_func", args=[])),
        get_return_statement(returns=get_tuple_literal(
            items=[
                get_function_call(
                                function="add", 
                                args=[get_identifier("a"), get_identifier("b"), get_identifier("c"), get_identifier("d")]
                ),
                get_identifier("b")
            ])
        )
    ]
)

# Test nested only return statement
nested_return_code = "func my_func() -> scalar { return Normal(Pert(1, 2, 3), Uniform(1, 2)) }"
nested_return_expected = get_function_def(
    name="my_func", 
    return_type="scalar", 
    body=[
        get_return_statement(
            get_function_call(function="Normal", args=[
                    get_function_call(function="Pert", args=[get_number_literal(1), get_number_literal(2), get_number_literal(3)]),
                    get_function_call(function="Uniform", args=[get_number_literal(1), get_number_literal(2)])
                ]
            )
        )
    ]
)

@pytest.mark.parametrize(
    "code, expected_function_def",
    [
    pytest.param(basic_func_code, basic_func_expected, id="basic_func_no_params"),
    pytest.param(space_tab_comments_code, space_tab_comments_expected, id="space_tab_comments"),
    pytest.param(tuple_2_elems_code, tuple_2_elems_expected, id="tuple_return_2_elements"),
    pytest.param(tuple_3_elems_code, tuple_3_elems_expected, id="tuple_return_3_elements"),
    pytest.param(param_1_code, param_1_expected, id="param_1"),
    pytest.param(param_2_code, param_2_expected, id="param_2"),
    pytest.param(param_3_code, param_3_expected, id="param_3"),
    pytest.param(docstring_code, docstring_expected, id="docstring"),
    pytest.param(tuple_simple_code, tuple_simple_expected, id="tuple_return_simple"),
    pytest.param(body_assignment_code, body_assignment_expected, id="body_simple_assignment"),
    pytest.param(body_assignment_and_return_code, body_assignment_and_return_expected, id="body_simple_assignment_and_return"),
    pytest.param(body_multi_assignment_code, body_multi_assignment_expected, id="body_multi_assignment"),
    pytest.param(body_complex_code_1, body_complex_expected_1, id="body_complex_1"),
    pytest.param(body_complex_code_2, body_complex_expected_2, id="body_complex_2"),
    pytest.param(nested_return_code, nested_return_expected, id="nested_only_return_statement"),
    ]
)
def test_function_definition_parsed_correctly(code, expected_function_def):
    """Tests that all ways to declare a function are parsed correctly."""
    ast = parse_valuascript(code)
    assert isinstance(ast, Root)
    assert len(ast.function_definitions) == 1
    actual_function_def = ast.function_definitions[0]
    assert_asts_equal(actual_function_def, expected_function_def)