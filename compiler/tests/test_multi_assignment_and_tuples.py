import pytest
import sys
import os
import json

# Make the compiler module available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode

# Import fixtures from the main integration test file for end-to-end testing
from tests.test_integration import find_engine_path, run_preview_integration


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
    assert "a" in recipe["variable_registry"]
    assert "b" in recipe["variable_registry"]


def test_builtin_function_multi_return():
    """Validates multi-assignment with a built-in function that returns a tuple."""
    script = """
    @iterations=1
    @output=amortization
    let past_rd = [100]
    let current_rd = 130
    let life = 3
    let cap_asset, amortization = capitalize_expense(current_rd, past_rd, life)
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    assert "cap_asset" in recipe["variable_registry"]
    assert "amortization" in recipe["variable_registry"]


# --- 2. ERROR HANDLING AND INVALID USAGE ---


@pytest.mark.parametrize(
    "script_body, expected_error_code",
    [
        pytest.param("func p() -> (scalar, scalar) { return (1,2) }\nlet a = p()", ErrorCode.ARGUMENT_COUNT_MISMATCH, id="assign_too_few_vars"),
        pytest.param("func p() -> (scalar, scalar) { return (1,2) }\nlet a,b,c = p()", ErrorCode.ARGUMENT_COUNT_MISMATCH, id="assign_too_many_vars"),
        pytest.param("let cap = capitalize_expense(1, [1], 1)", ErrorCode.ARGUMENT_COUNT_MISMATCH, id="assign_too_few_from_builtin"),
        pytest.param("func p() -> (scalar, scalar) { return 1 }", ErrorCode.RETURN_TYPE_MISMATCH, id="udf_return_single_for_tuple"),
        pytest.param("func p() -> (scalar, scalar) { return (1, [2]) }", ErrorCode.RETURN_TYPE_MISMATCH, id="udf_return_wrong_type_in_tuple"),
        pytest.param("func p() -> (scalar, scalar) { return (1, 2, 3) }", ErrorCode.RETURN_TYPE_MISMATCH, id="udf_return_tuple_of_wrong_size"),
        pytest.param("func p() -> (scalar, scalar) { return (1,2) }\nlet a, a = p()", ErrorCode.DUPLICATE_VARIABLE, id="duplicate_var_in_multi_assignment"),
        pytest.param("let a, b = (1, 2)", ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT, id="assign_from_tuple_literal_not_allowed"),
    ],
)
def test_multi_assignment_semantic_errors(script_body, expected_error_code):
    """A comprehensive suite of tests for semantic and arity errors related to tuple returns and multi-assignment."""
    full_script = f"@iterations=1\n@output=x\n{script_body}\nlet x=1"
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(full_script)
    assert e.value.code == expected_error_code


# --- 3. BYTECODE GENERATION & LINKER VERIFICATION ---


def test_linker_bytecode_for_multi_assignment():
    """Inspects the compiled recipe to ensure the linker generates the unified 'execution_assignment' step."""
    script = """
    @iterations=1
    @output=b
    let p = [10]
    let a, b = capitalize_expense(1, p, 2)
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    registry = recipe["variable_registry"]
    a_idx, b_idx = registry.index("a"), registry.index("b")

    all_steps = recipe["pre_trial_steps"] + recipe["per_trial_steps"]
    assign_step = next((s for s in all_steps if s.get("function") == "capitalize_expense"), None)

    assert assign_step is not None, "capitalize_expense step not found in bytecode"
    assert assign_step["type"] == "execution_assignment"  # Unified type
    assert "result_index" not in assign_step  # Old key is gone
    assert assign_step["result_indices"] == [a_idx, b_idx]  # New key is correct


# --- 4. END-TO-END ENGINE INTEGRATION ---


def test_end_to_end_multi_assignment_integration(find_engine_path):
    """Runs the full compiler-to-engine pipeline and verifies the final value of a variable from a multi-assignment."""
    script = """
    @iterations=1
    @output=final_val
    func get_constants() -> (scalar, scalar) {
        return (100, 2.5)
    }
    let base, multiplier = get_constants()
    let final_val = base * multiplier
    """
    result = run_preview_integration(script, "final_val", find_engine_path)
    assert result.get("status") == "success"
    assert result.get("type") == "scalar"
    assert pytest.approx(result.get("value")) == 250.0
