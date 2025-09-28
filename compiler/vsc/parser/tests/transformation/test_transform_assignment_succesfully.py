import pytest

from vsc.parser.classes import *
from vsc.parser.parser import parse_valuascript

from ..utils.assertion_helper import assert_asts_equal
from ..utils.factory_helpers import *

# Test literal assignments -> la
literal_num_code = "let a = 1_000.25"
literal_num_exp = get_literal_assignment(target="a", value=get_number_literal(1000.25))

literal_string_code = 'let a = "string"'
literal_string_exp = get_literal_assignment(target="a", value=get_string_literal("string"))

literal_bool_code_1 = "let a = true"
literal_bool_code_2 = "let a = false"
literal_bool_exp_1 = get_literal_assignment(target="a", value=get_boolean_literal(True))
literal_bool_exp_2 = get_literal_assignment(target="a", value=get_boolean_literal(False))

literal_vector_code_1 = "let a = [1,2,3]"
literal_vector_exp_1 = get_literal_assignment(target="a", value=get_vector_literal([get_number_literal(1), get_number_literal(2), get_number_literal(3)]))

literal_vector_code_2 = "let a = []"
literal_vector_exp_2 = get_literal_assignment(target="a", value=get_vector_literal([]))

copy_assignment_code = "let a = b"
copy_assignment_exp = get_copy_assignment(target="a", source="b")

# Test execution assignment -> ea
execution_func_call_code = "let a = Normal(1, 2)"
execution_func_call_exp = get_execution_assignment(target="a", expression=get_function_call("Normal", args=[get_number_literal(1), get_number_literal(2)]))

execution_func_call_nested_code = "let a = Normal(Pert(1, 2, 3), 1) * 10 + 3"
execution_func_call_nested_exp = get_execution_assignment(
    target="a",
    expression=get_function_call(
        "add",
        args=[
            get_function_call(
                "multiply",
                args=[
                    get_function_call("Normal", args=[get_function_call("Pert", args=[get_number_literal(1), get_number_literal(2), get_number_literal(3)]), get_number_literal(1)]),
                    get_number_literal(10),
                ],
            ),
            get_number_literal(3),
        ],
    ),
)

execution_vec_elem_access_code = "let a = my_vec[0] + 10"
execution_vec_elem_access_exp = get_execution_assignment(target="a", expression=get_function_call("add", args=[get_element_access("my_vec", get_number_literal(0)), get_number_literal(10)]))

execution_vec_elem_delete_code = "let a = my_vec[:1] + 10"
execution_vec_elem_delete_exp = get_execution_assignment(target="a", expression=get_function_call("add", args=[get_delete_element("my_vec", get_number_literal(1)), get_number_literal(10)]))
execution_comparison_and_precedence_code = "let a = x > 5 and y < 10"
execution_comparison_and_precedence_exp = get_execution_assignment(
    target="a",
    expression=get_function_call(
        function="__and__",
        args=[
            get_function_call(function="__gt__", args=[get_identifier("x"), get_number_literal(5)]),
            get_function_call(function="__lt__", args=[get_identifier("y"), get_number_literal(10)]),
        ],
    ),
)

# Test variadic grouping
variadic_code = "let a = 1 + 2 + 3 + 4"
variadic_exp = get_execution_assignment(
    target="a",
    expression=get_function_call(
        function="add",
        args=[
            get_number_literal(1),
            get_number_literal(2),
            get_number_literal(3),
            get_number_literal(4),
        ],
    ),
)

variadic_nested_code = "let a = 1 + (2 + 3) + 4"
variadic_nested_exp = get_execution_assignment(
    target="a",
    expression=get_function_call(
        function="add",
        args=[
            get_number_literal(1),
            get_function_call(function="add", args=[get_number_literal(2), get_number_literal(3)]),
            get_number_literal(4),
        ],
    ),
)

# Test precedence
precedence_default_code = "let a = 10 + 11 * 22"
precedence_default_exp = get_execution_assignment(
    target="a", expression=get_function_call("add", args=[get_number_literal(10), get_function_call("multiply", args=[get_number_literal(11), get_number_literal(22)])])
)

precedence_modified_code = "let a = (10 + 11) * 22"
precedence_modified_exp = get_execution_assignment(
    target="a",
    expression=get_function_call(
        "multiply",
        args=[
            get_function_call("add", args=[get_number_literal(10), get_number_literal(11)]),
            get_number_literal(22),
        ],
    ),
)

# Test conditional assignment -> cd
conditional_basic_code = "let a = if true then 4 else 5"
conditional_basic_exp = get_conditional_assignment(target="a", condition=get_boolean_literal(True), then_expr=get_number_literal(4), else_expr=get_number_literal(5))

conditional_cond_is_other_var_code = "let a = if b then 4 else 5"
conditional_cond_is_other_var_exp = get_conditional_assignment(target="a", condition=get_identifier("b"), then_expr=get_number_literal(4), else_expr=get_number_literal(5))

conditional_returns_are_other_vars_code = "let a = if true then b else c"
conditional_returns_are_other_vars_exp = get_conditional_assignment(target="a", condition=get_boolean_literal(True), then_expr=get_identifier("b"), else_expr=get_identifier("c"))

conditional_nested_else_code = "let a = if true then 1 else if false then 13 else 14"
conditional_nested_else_exp = get_conditional_assignment(
    target="a",
    condition=get_boolean_literal(True),
    then_expr=get_number_literal(1),
    else_expr=get_conditional_expression(condition=get_boolean_literal(False), then_expr=get_number_literal(13), else_expr=get_number_literal(14)),
)

conditional_then_is_func_call_code = "let a = if b then some_func(1) else 5"
conditional_then_is_func_call_exp = get_conditional_assignment(
    target="a", condition=get_identifier("b"), then_expr=get_function_call("some_func", args=[get_number_literal(1)]), else_expr=get_number_literal(5)
)

conditional_cond_is_func_code = "let a = if some_func() then b else c"
conditional_cond_is_func_exp = get_conditional_assignment(target="a", condition=get_function_call("some_func", args=[]), then_expr=get_identifier("b"), else_expr=get_identifier("c"))

conditional_as_func_arg_code = "let a = my_func(if x then 1 else 2)"
conditional_as_func_arg_exp = get_execution_assignment(
    target="a", expression=get_function_call(function="my_func", args=[get_conditional_expression(condition=get_identifier("x"), then_expr=get_number_literal(1), else_expr=get_number_literal(2))])
)

# Test multi-assignment -> ma
multi_assignment_basic_code = "let a, b = some_func()"
multi_assignment_basic_exp = get_multi_assignment(targets=[get_identifier("a"), get_identifier("b")], expression=get_function_call(function="some_func", args=[]))

multi_assignment_3_vars_code = "let a, b, c = some_func()"
multi_assignment_3_vars_exp = get_multi_assignment(targets=[get_identifier("a"), get_identifier("b"), get_identifier("c")], expression=get_function_call(function="some_func", args=[]))

multi_copy_assignment_var_code = "let a, b = my_tuple"
multi_copy_assignment_var_exp = get_multi_copy_assignment(targets=["a", "b"], source="my_tuple")

multi_copy_assignment_tuple_literal_code = "let a, b = (1, Normal(1,2))"
multi_copy_assignment_tuple_literal_exp = get_multi_copy_assignment_tuple(
    targets=["a", "b"], source=[get_number_literal(1), get_function_call(function="Normal", args=[get_number_literal(1), get_number_literal(2)])]
)


@pytest.mark.parametrize(
    "code, expected_assignment",
    [
        pytest.param(literal_num_code, literal_num_exp, id="la_number"),
        pytest.param(literal_string_code, literal_string_exp, id="la_string"),
        pytest.param(literal_bool_code_1, literal_bool_exp_1, id="la_bool_1"),
        pytest.param(literal_bool_code_2, literal_bool_exp_2, id="la_bool_2"),
        pytest.param(literal_vector_code_1, literal_vector_exp_1, id="la_vector_1"),
        pytest.param(literal_vector_code_2, literal_vector_exp_2, id="la_vector_2"),
        pytest.param(copy_assignment_code, copy_assignment_exp, id="copy_assignment"),
        pytest.param(execution_func_call_code, execution_func_call_exp, id="ea_func_call"),
        pytest.param(execution_func_call_nested_code, execution_func_call_nested_exp, id="ea_func_call_nested"),
        pytest.param(execution_vec_elem_access_code, execution_vec_elem_access_exp, id="ea_element_access"),
        pytest.param(execution_vec_elem_delete_code, execution_vec_elem_delete_exp, id="ea_element_deletion"),
        pytest.param(execution_comparison_and_precedence_code, execution_comparison_and_precedence_exp, id="ea_comparison_and_precedence"),
        pytest.param(variadic_code, variadic_exp, id="ea_variadic"),
        pytest.param(variadic_nested_code, variadic_nested_exp, id="ea_nested_variadic"),
        pytest.param(conditional_as_func_arg_code, conditional_as_func_arg_exp, id="ea_conditional_as_func_arg_code"),
        pytest.param(precedence_default_code, precedence_default_exp, id="precedence_default"),
        pytest.param(precedence_modified_code, precedence_modified_exp, id="precedence_modified"),
        pytest.param(conditional_basic_code, conditional_basic_exp, id="cd_basic"),
        pytest.param(conditional_cond_is_other_var_code, conditional_cond_is_other_var_exp, id="cd_cond_is_other_var"),
        pytest.param(conditional_returns_are_other_vars_code, conditional_returns_are_other_vars_exp, id="cd_returns_are_other_vars"),
        pytest.param(conditional_nested_else_code, conditional_nested_else_exp, id="cd_nested_else"),
        pytest.param(conditional_then_is_func_call_code, conditional_then_is_func_call_exp, id="cd_then_is_func_call"),
        pytest.param(conditional_cond_is_func_code, conditional_cond_is_func_exp, id="cd_condition_is_func"),
        pytest.param(multi_assignment_basic_code, multi_assignment_basic_exp, id="ma_basic"),
        pytest.param(multi_assignment_3_vars_code, multi_assignment_3_vars_exp, id="ma_3_vars"),
        pytest.param(multi_copy_assignment_var_code, multi_copy_assignment_var_exp, id="multi_copy_assignment_var"),
        pytest.param(multi_copy_assignment_tuple_literal_code, multi_copy_assignment_tuple_literal_exp, id="multi_copy_assignment_tuple_literal_"),
    ],
)
def test_assignment_parsed_correctly(code, expected_assignment):
    """Tests that all assignment types are parsed correctly."""
    ast = parse_valuascript(code)
    assert isinstance(ast, Root)
    assert len(ast.execution_steps) >= 1

    actual_assignment = ast.execution_steps[0]
    assert_asts_equal(actual_assignment, expected_assignment)
