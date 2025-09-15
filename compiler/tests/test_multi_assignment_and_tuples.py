import pytest
import sys
import os
import json

# Make the compiler module available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode

# Import fixtures from the main integration test file for end-to-end testing
from test_integration import find_engine_path, run_preview_integration


# --- 1. VALID MULTI-ASSIGNMENT AND TUPLE USAGE ---


def test_udf_multi_return_and_assignment():
    """Tests the core feature: defining a UDF with a tuple return type and assigning its result to multiple variables."""
    script = """
    @iterations=1
    @output=b
    func get_pair() -> (scalar, scalar) {
        return (10, 20)
    }
    let a, b = get_pair()
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    # Check that both 'a' and 'b' are in the final registry
    assert "a" in recipe["variable_registry"]
    assert "b" in recipe["variable_registry"]


def test_builtin_function_multi_return():
    """Validates multi-assignment with a built-in function that returns a tuple."""
    script = """
    @iterations=1
    @output=amortization
    let past_rd = [100, 110, 120]
    let current_rd = 130
    let life = 3
    let cap_asset, amortization = capitalize_expense(current_rd, past_rd, life)
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    assert "cap_asset" in recipe["variable_registry"]
    assert "amortization" in recipe["variable_registry"]


def test_multi_return_with_mixed_types():
    """Ensures tuple return types can consist of different types, like scalar and vector."""
    script = """
    @iterations=1
    @output=s
    func get_mixed() -> (vector, scalar) {
        return ([1, 2], 100)
    }
    let v, s = get_mixed()
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    assert "v" in recipe["variable_registry"]
    assert "s" in recipe["variable_registry"]


# --- 2. INTEGRATION WITH OPTIMIZATIONS ---


def test_stochasticity_propagation_from_tuple():
    """
    CRITICAL: Validates that if one of the returned values in a tuple is stochastic,
    the corresponding variable (and only that one) taints its dependency chain.
    """
    script = """
    @iterations=100
    @output=final_stochastic
    func get_values() -> (scalar, scalar) {
        return (10, Normal(100, 5))
    }
    let deterministic_var, stochastic_var = get_values()
    let final_stochastic = stochastic_var + 1
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    registry = recipe["variable_registry"]
    pre_trial_vars = {registry[step["result_index"]] for step in recipe["pre_trial_steps"]}
    per_trial_vars = {registry[step["result_index"]] for step in recipe["per_trial_steps"]}

    # The deterministic part of the result should be pre-trial
    assert "deterministic_var" in pre_trial_vars
    # The stochastic part and its dependents must be per-trial
    assert "stochastic_var" in per_trial_vars
    assert "final_stochastic" in per_trial_vars


def test_dce_on_partially_used_multi_assignment():
    """
    Tests that if a multi-assignment occurs but only one of the variables is
    used, the other is correctly eliminated as dead code.
    """
    script = """
    @iterations=1
    @output=used_var
    func get_pair() -> (scalar, scalar) {
        return (1, 2)
    }
    let used_var, unused_var = get_pair()
    """
    recipe = compile_valuascript(script, optimize=True)
    assert recipe is not None
    # The final registry should only contain the live variable
    assert set(recipe["variable_registry"]) == {"used_var"}


def test_dce_on_completely_unused_multi_assignment():
    """
    Tests that if a multi-assignment's results are never used, the entire
    function call and all result variables are eliminated.
    """
    script = """
    @iterations=1
    @output=final_output
    func get_pair() -> (scalar, scalar) {
        let internal_a = 100
        let internal_b = 200
        return (internal_a, internal_b)
    }
    let unused_a, unused_b = get_pair()
    let final_output = 42
    """
    recipe = compile_valuascript(script, optimize=True)
    assert recipe is not None
    final_vars = set(recipe["variable_registry"])
    assert final_vars == {"final_output"}
    # Ensure no trace of the unused call remains
    assert "unused_a" not in final_vars
    assert "unused_b" not in final_vars
    assert not any(v.startswith("__get_pair_") for v in final_vars)


# --- 3. ERROR HANDLING AND INVALID USAGE ---


@pytest.mark.parametrize(
    "script_body, expected_error_code",
    [
        pytest.param(
            "func p() -> (scalar, scalar) { return (1,2) }\nlet a = p()",
            ErrorCode.ARGUMENT_COUNT_MISMATCH,
            id="assign_too_few_vars",
        ),
        pytest.param(
            "func p() -> (scalar, scalar) { return (1,2) }\nlet a,b,c = p()",
            ErrorCode.ARGUMENT_COUNT_MISMATCH,
            id="assign_too_many_vars",
        ),
        pytest.param(
            "let cap, amort, extra = capitalize_expense(1, [1], 1)",
            ErrorCode.ARGUMENT_COUNT_MISMATCH,
            id="assign_too_many_from_builtin",
        ),
        pytest.param(
            "func p() -> (scalar, scalar) { return 1 }",
            ErrorCode.RETURN_TYPE_MISMATCH,
            id="udf_return_single_for_tuple",
        ),
        pytest.param(
            "func p() -> (scalar, scalar) { return (1, [2]) }",
            ErrorCode.RETURN_TYPE_MISMATCH,
            id="udf_return_wrong_type_in_tuple",
        ),
        pytest.param(
            "func p() -> (scalar, scalar) { return (1, 2, 3) }",
            ErrorCode.RETURN_TYPE_MISMATCH,
            id="udf_return_tuple_of_wrong_size",
        ),
        pytest.param(
            "func p() -> (scalar, scalar) { return (1,2) }\nlet a, a = p()",
            ErrorCode.DUPLICATE_VARIABLE,
            id="duplicate_var_in_multi_assignment",
        ),
        pytest.param(
            "let a, b = (1, 2)",
            ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT,
            id="assign_from_tuple_literal_not_allowed",
        ),
    ],
)
def test_multi_assignment_semantic_errors(script_body, expected_error_code):
    """A comprehensive suite of tests for semantic and arity errors related to tuple returns and multi-assignment."""
    full_script = f"@iterations=1\n@output=x\n{script_body}\nlet x=1"
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(full_script)
    assert e.value.code == expected_error_code


# --- 4. INTEGRATION WITH MODULE SYSTEM ---


def test_import_and_use_multi_return_udf(tmp_path):
    """
    Tests that a UDF returning a tuple can be correctly imported from another
    module and used in the main script.
    """
    # ARRANGE: Create module and main files
    module_content = """
    @module
    func get_module_pair() -> (scalar, scalar) {
        let val1 = 1000
        return (val1, 2000)
    }
    """
    module_path = tmp_path / "utils.vs"
    module_path.write_text(module_content)

    main_content = f"""
    @import "{module_path.name}"
    @iterations=1
    @output=y
    let x, y = get_module_pair()
    """
    main_path = tmp_path / "main.vs"
    main_path.write_text(main_content)

    # ACT & ASSERT
    recipe = compile_valuascript(main_content, file_path=str(main_path))
    assert recipe is not None
    assert "x" in recipe["variable_registry"]
    assert "y" in recipe["variable_registry"]
    # Check that the UDF was correctly inlined from the module
    assert any(v.startswith("__get_module_pair_") for v in recipe["variable_registry"])


# --- 5. ADVANCED SEMANTIC VALIDATION ---


def test_multi_assignment_in_conditional_expression():
    """DEEP TEST: Ensures the type checker can validate that both branches of an if/else return the same tuple signature."""
    script = """
    @iterations=1
    @output=y
    func high_scenario() -> (scalar, scalar) { return (100, 200) }
    func low_scenario() -> (scalar, scalar) { return (10, 20) }
    let selector = true
    let x, y = if selector then high_scenario() else low_scenario()
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    assert "x" in recipe["variable_registry"]
    assert "y" in recipe["variable_registry"]


def test_multi_assignment_conditional_type_mismatch_fails():
    """DEEP TEST: Ensures the compiler fails if branches of an if/else have different tuple signatures."""
    script = """
    @iterations=1
    @output=y
    func scenario_a() -> (scalar, scalar) { return (1, 2) }
    func scenario_b() -> (scalar, vector) { return (3, [4]) }
    let selector = true
    let x, y = if selector then scenario_a() else scenario_b()
    """
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.IF_ELSE_TYPE_MISMATCH


# --- 6. BYTECODE GENERATION & LINKER VERIFICATION ---


def test_linker_bytecode_for_multi_assignment():
    """DEEP TEST: Inspects the compiled recipe to ensure the linker generates the correct low-level bytecode for multi-assignment."""
    # Use a built-in function because UDFs are inlined into single assignments.
    # Built-ins are not inlined, so they will produce a direct multi-assignment step.
    script = """
    @iterations=1
    @output=b
    let p = [10]
    let c = 1
    let l = 2
    let a, b = capitalize_expense(c, p, l)
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    # Find the indices for the result variables
    registry = recipe["variable_registry"]
    a_index = registry.index("a")
    b_index = registry.index("b")

    # Find the step that produces these variables
    all_steps = recipe["pre_trial_steps"] + recipe["per_trial_steps"]
    multi_assign_step = None
    for step in all_steps:
        # The order of indices might not be guaranteed, so check as a set.
        if set(step.get("result_indices", [])) == {a_index, b_index}:
            multi_assign_step = step
            break

    assert multi_assign_step is not None, "Multi-assignment step was not found in the bytecode"
    assert multi_assign_step["type"] == "multi_execution_assignment"
    assert multi_assign_step["function"] == "capitalize_expense"
    assert len(multi_assign_step["args"]) == 3


# --- 7. END-TO-END ENGINE INTEGRATION ---


def test_end_to_end_multi_assignment_integration(find_engine_path):
    """DEEP TEST: Runs the full compiler-to-engine pipeline and verifies the final value of a variable from a multi-assignment."""
    script = """
    @iterations=1
    @output=final_val
    func get_constants() -> (scalar, scalar) {
        return (100, 2.5)
    }
    let base, multiplier = get_constants()
    let final_val = base * multiplier
    """
    # Use the preview feature to get the value of the final variable
    result = run_preview_integration(script, "final_val", find_engine_path)

    assert result.get("status") == "success"
    assert result.get("type") == "scalar"
    assert pytest.approx(result.get("value")) == 250.0
