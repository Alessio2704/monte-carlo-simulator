import pytest
import json
from typing import Dict, Any, List

# The module we are testing
from vsc.bytecode_generation.ir_lowerer import IRLowerer
from vsc.optimizer.ir_validator import IRValidator

from textwrap import dedent
from vsc.compiler import compile_valuascript


# --- Test Helpers ---


def create_dummy_file(tmp_path, filename, content):
    """Helper to create a temporary file for testing imports."""
    path = tmp_path / filename
    path.write_text(dedent(content).strip())
    return str(path)


def pretty_format_ir(ir: Dict[str, Any]) -> str:
    """Helper to format IR for readable test failure messages."""
    return json.dumps(ir, indent=2)


@pytest.fixture
def base_model() -> Dict[str, Any]:
    """Provides a clean, boilerplate model object for tests."""
    return {
        "global_variables": {},
        "all_signatures": {
            "Normal": {"return_type": "scalar", "is_stochastic": True},
            "multiply": {"return_type": "scalar", "is_stochastic": False, "variadic": True},
            "add": {"return_type": "scalar", "is_stochastic": False, "variadic": True},
            "__and__": {"return_type": "boolean", "is_stochastic": False, "variadic": True},
        },
    }


def validate_ir(ir: List[Dict[str, Any]], pre_defined_vars: List[str] = None):
    """Helper to run the IR validator with optional pre-defined variables."""
    validator = IRValidator(ir)
    if pre_defined_vars:
        validator.defined_vars.update(pre_defined_vars)
    validator.validate()


# --- Comprehensive Test Suite for IRLowerer ---


def test_lowers_nested_conditional_assignments_correctly(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {
        "tax_rate": {"inferred_type": "scalar"},
        "is_high_income": {"inferred_type": "boolean"},
        "is_medium_income": {"inferred_type": "boolean"},
    }
    partitioned_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {
                "type": "conditional_assignment",
                "result": ["tax_rate"],
                "condition": "is_high_income",
                "then_expr": 0.4,
                "else_expr": {"type": "conditional_expression", "condition": "is_medium_income", "then_expr": 0.3, "else_expr": 0.2},
                "line": 59,
            }
        ],
    }
    final_expected_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {"type": "jump_if_false", "condition": "is_medium_income", "target": "__else_label_0", "line": 59},
            {"type": "literal_assignment", "result": ["__temp_lifted_1"], "value": 0.3, "line": 59},
            {"type": "jump", "target": "__end_label_1", "line": 59},
            {"type": "label", "name": "__else_label_0", "line": 59},
            {"type": "literal_assignment", "result": ["__temp_lifted_1"], "value": 0.2, "line": 59},
            {"type": "label", "name": "__end_label_1", "line": 59},
            {"type": "jump_if_false", "condition": "is_high_income", "target": "__else_label_2", "line": 59},
            {"type": "literal_assignment", "result": ["tax_rate"], "value": 0.4, "line": 59},
            {"type": "jump", "target": "__end_label_3", "line": 59},
            {"type": "label", "name": "__else_label_2", "line": 59},
            {"type": "copy", "result": ["tax_rate"], "source": "__temp_lifted_1", "line": 59},
            {"type": "label", "name": "__end_label_3", "line": 59},
        ],
    }

    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()

    # ASSERT
    assert actual_result == final_expected_ir
    validate_ir(actual_result["per_trial_steps"], ["is_high_income", "is_medium_income"])


def test_lifts_simple_nested_function_call(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {"x": {"inferred_type": "scalar"}, "result": {"inferred_type": "scalar"}}
    partitioned_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [{"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["x", {"function": "Normal", "args": [0, 1]}], "line": 10}],
    }
    expected_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {"type": "execution_assignment", "result": ["__temp_lifted_1"], "function": "Normal", "args": [0, 1], "line": 10},
            {"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["x", "__temp_lifted_1"], "line": 10},
        ],
    }

    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()

    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["per_trial_steps"], ["x"])


@pytest.mark.parametrize("func_name, var_type", [("add", "scalar"), ("__and__", "boolean")])
def test_decomposes_variadic_operations_into_binary_chain(base_model, func_name, var_type):
    """
    Explicitly tests that a single variadic instruction like add(a, b, c, d)
    is correctly decomposed into a chain of simple binary operations.
    """
    # ARRANGE
    model = base_model
    model["global_variables"] = {
        "a": {"inferred_type": var_type},
        "b": {"inferred_type": var_type},
        "c": {"inferred_type": var_type},
        "d": {"inferred_type": var_type},
        "result": {"inferred_type": var_type},
    }
    partitioned_ir = {
        "pre_trial_steps": [{"type": "execution_assignment", "result": ["result"], "function": func_name, "args": ["a", "b", "c", "d"], "line": 10}],
        "per_trial_steps": [],
    }
    expected_ir = {
        "pre_trial_steps": [
            {"type": "execution_assignment", "result": ["__temp_lifted_1"], "function": func_name, "args": ["a", "b"], "line": 10},
            {"type": "execution_assignment", "result": ["__temp_lifted_2"], "function": func_name, "args": ["__temp_lifted_1", "c"], "line": 10},
            {"type": "execution_assignment", "result": ["result"], "function": func_name, "args": ["__temp_lifted_2", "d"], "line": 10},
        ],
        "per_trial_steps": [],
    }

    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, updated_model = lowerer.lower()

    # ASSERT
    assert actual_result == expected_ir
    assert "__temp_lifted_1" in updated_model["global_variables"]
    assert "__temp_lifted_2" in updated_model["global_variables"]
    validate_ir(actual_result["pre_trial_steps"], ["a", "b", "c", "d"])


def test_lifts_multiple_nested_calls_in_one_instruction(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {"result": {"inferred_type": "scalar"}}
    partitioned_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {"type": "execution_assignment", "result": ["result"], "function": "add", "args": [{"function": "Normal", "args": [0, 1]}, {"function": "Normal", "args": [5, 2]}], "line": 20}
        ],
    }
    expected_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {"type": "execution_assignment", "result": ["__temp_lifted_1"], "function": "Normal", "args": [0, 1], "line": 20},
            {"type": "execution_assignment", "result": ["__temp_lifted_2"], "function": "Normal", "args": [5, 2], "line": 20},
            {"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["__temp_lifted_1", "__temp_lifted_2"], "line": 20},
        ],
    }
    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["per_trial_steps"])


def test_lifts_deeply_nested_function_call(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {"x": {"inferred_type": "scalar"}, "y": {"inferred_type": "scalar"}, "result": {"inferred_type": "scalar"}}
    partitioned_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["x", {"function": "multiply", "args": ["y", {"function": "Normal", "args": [0, 1]}]}], "line": 30}
        ],
    }
    expected_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {"type": "execution_assignment", "result": ["__temp_lifted_1"], "function": "Normal", "args": [0, 1], "line": 30},
            {"type": "execution_assignment", "result": ["__temp_lifted_2"], "function": "multiply", "args": ["y", "__temp_lifted_1"], "line": 30},
            {"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["x", "__temp_lifted_2"], "line": 30},
        ],
    }
    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["per_trial_steps"], ["x", "y"])


def test_lowers_identity_to_copy(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {"a": {"inferred_type": "scalar"}, "b": {"inferred_type": "scalar"}}
    partitioned_ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["a"], "function": "identity", "args": ["b"], "line": 10}], "per_trial_steps": []}
    expected_ir = {"pre_trial_steps": [{"type": "copy", "result": ["a"], "source": "b", "line": 10}], "per_trial_steps": []}
    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["pre_trial_steps"], ["b"])


def test_lowers_identity_to_copy_for_tuples(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = ({"z": {"inferred_type": "vector", "is_stochastic": False}, "d": {"inferred_type": "vector", "is_stochastic": False}},)
    partitioned_ir = {
        "pre_trial_steps": [
            {"type": "literal_assignment", "result": ["__get_base_segment_data_1__revenues"], "value": [1, 2, 3], "line": 5},
            {"type": "literal_assignment", "result": ["__get_base_segment_data_1__operating_margin"], "value": [4, 5, 6], "line": 6},
            {
                "type": "execution_assignment",
                "result": ["z", "d"],
                "function": "identity",
                "args": [["__get_base_segment_data_1__revenues", "__get_base_segment_data_1__operating_margin"]],
                "line": 11,
            },
        ],
        "per_trial_steps": [],
    }

    expected_ir = {
        "pre_trial_steps": [
            {"type": "literal_assignment", "result": ["__get_base_segment_data_1__revenues"], "value": [1, 2, 3], "line": 5},
            {"type": "literal_assignment", "result": ["__get_base_segment_data_1__operating_margin"], "value": [4, 5, 6], "line": 6},
            {"type": "copy", "result": ["z"], "source": "__get_base_segment_data_1__revenues", "line": 11},
            {"type": "copy", "result": ["d"], "source": "__get_base_segment_data_1__operating_margin", "line": 11},
        ],
        "per_trial_steps": [],
    }

    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["pre_trial_steps"], ["b"])


def test_counters_continue_across_partitions(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {"cond": {"inferred_type": "boolean"}, "x": {"inferred_type": "scalar"}}
    partitioned_ir = {
        "pre_trial_steps": [{"type": "conditional_assignment", "result": ["x"], "condition": "cond", "then_expr": 1, "else_expr": 2, "line": 1}],
        "per_trial_steps": [{"type": "execution_assignment", "result": ["x"], "function": "add", "args": ["x", {"function": "Normal", "args": [0, 1]}], "line": 2}],
    }
    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert lowerer.label_counter == 2
    assert lowerer.temp_var_counter >= 1
    validate_ir(actual_result["pre_trial_steps"], ["cond"])
    validate_ir(actual_result["per_trial_steps"], ["x"])


def test_handles_empty_ir_gracefully(base_model):
    # ARRANGE
    partitioned_ir = {"pre_trial_steps": [], "per_trial_steps": []}
    # ACT
    lowerer = IRLowerer(partitioned_ir, base_model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert actual_result == partitioned_ir


def test_preserves_ir_with_no_lowerable_instructions(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {"a": {"inferred_type": "scalar"}, "b": {"inferred_type": "scalar"}}
    partitioned_ir = {
        "pre_trial_steps": [{"type": "literal_assignment", "result": ["a"], "value": 10, "line": 1}, {"type": "execution_assignment", "result": ["b"], "function": "add", "args": ["a", 5], "line": 2}],
        "per_trial_steps": [],
    }
    original_ir = json.loads(json.dumps(partitioned_ir))
    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert actual_result == original_ir
    validate_ir(actual_result["pre_trial_steps"])


def test_kitchen_sink_nested_conditional_with_nested_function(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {
        "result": {"inferred_type": "scalar"},
        "is_critical": {"inferred_type": "boolean"},
        "use_stochastic": {"inferred_type": "boolean"},
    }
    partitioned_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {
                "type": "conditional_assignment",
                "result": ["result"],
                "condition": "is_critical",
                "then_expr": 100,
                "else_expr": {
                    "type": "conditional_expression",
                    "condition": "use_stochastic",
                    "then_expr": {"function": "Normal", "args": [50, 5]},
                    "else_expr": 25,
                },
                "line": 40,
            }
        ],
    }
    full_expected = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {"type": "execution_assignment", "result": ["__temp_lifted_1"], "function": "Normal", "args": [50, 5], "line": 40},
            {"type": "jump_if_false", "condition": "use_stochastic", "target": "__else_label_0", "line": 40},
            {"type": "copy", "result": ["__temp_lifted_2"], "source": "__temp_lifted_1", "line": 40},
            {"type": "jump", "target": "__end_label_1", "line": 40},
            {"type": "label", "name": "__else_label_0", "line": 40},
            {"type": "literal_assignment", "result": ["__temp_lifted_2"], "value": 25, "line": 40},
            {"type": "label", "name": "__end_label_1", "line": 40},
            {"type": "jump_if_false", "condition": "is_critical", "target": "__else_label_2", "line": 40},
            {"type": "literal_assignment", "result": ["result"], "value": 100, "line": 40},
            {"type": "jump", "target": "__end_label_3", "line": 40},
            {"type": "label", "name": "__else_label_2", "line": 40},
            {"type": "copy", "result": ["result"], "source": "__temp_lifted_2", "line": 40},
            {"type": "label", "name": "__end_label_3", "line": 40},
        ],
    }
    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, _ = lowerer.lower()
    # ASSERT
    assert actual_result == full_expected
    validate_ir(actual_result["per_trial_steps"], ["is_critical", "use_stochastic"])


def test_lifts_function_call_from_condition(base_model):
    # ARRANGE
    model = base_model
    model["global_variables"] = {"a": {"inferred_type": "scalar"}, "result": {"inferred_type": "scalar"}}
    model["all_signatures"]["greater_than"] = {"return_type": "boolean"}

    partitioned_ir = {
        "pre_trial_steps": [{"type": "conditional_assignment", "result": ["result"], "condition": {"function": "greater_than", "args": ["a", 10]}, "then_expr": 100, "else_expr": 200, "line": 50}],
        "per_trial_steps": [],
    }
    expected_ir = {
        "pre_trial_steps": [
            {"type": "execution_assignment", "result": ["__temp_lifted_1"], "function": "greater_than", "args": ["a", 10], "line": 50},
            {"type": "jump_if_false", "condition": "__temp_lifted_1", "target": "__else_label_0", "line": 50},
            {"type": "literal_assignment", "result": ["result"], "value": 100, "line": 50},
            {"type": "jump", "target": "__end_label_1", "line": 50},
            {"type": "label", "name": "__else_label_0", "line": 50},
            {"type": "literal_assignment", "result": ["result"], "value": 200, "line": 50},
            {"type": "label", "name": "__end_label_1", "line": 50},
        ],
        "per_trial_steps": [],
    }
    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    actual_result, updated_model = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    assert updated_model["global_variables"]["__temp_lifted_1"]["inferred_type"] == "boolean"
    validate_ir(actual_result["pre_trial_steps"], ["a"])


def test_pipeline_handles_multi_return_udf_correctly(tmp_path):
    """
    This is an integration test for the bug where lifting a multi-return
    function call would only create a single temporary variable.

    It ensures that the IR Lowerer is "signature-aware" and creates the
    correct number of temporary variables, leading to a valid final IR.
    """

    main_script = dedent(
        """
        @iterations = 1
        @output = sir1

        func get_sir() -> (vector, vector, vector) {
            let population = 1_000_000
            let initial_infected = 10
            let transmission_rate = 0.35
            let recovery_rate = 1 / 14

            return SirModel(
                population - initial_infected,
                initial_infected,
                0,
                transmission_rate,
                recovery_rate,
                120, # Simulate for 120 days
                1.0
            )
        }

        let sir1, sir2, sir3 = get_sir()
        """
    ).strip()

    main_file_path = create_dummy_file(tmp_path, "main.vs", main_script)

    # Define the expected final, lowered IR structure. The multi-assignment copy
    # from the UDF's return is now decomposed into a sequence of single copies.
    expected_lowered_ir = {
        "pre_trial_steps": [
            {
                "type": "execution_assignment",
                "result": ["__temp_lifted_1", "__temp_lifted_2", "__temp_lifted_3"],
                "function": "SirModel",
                "args": [999990.0, 10.0, 0.0, 0.35, 0.07142857142857142, 120.0, 1.0],
                "line": 21,
            },
            {"type": "copy", "result": ["sir1"], "source": "__temp_lifted_1", "line": 21},
            {"type": "copy", "result": ["sir2"], "source": "__temp_lifted_2", "line": 21},
            {"type": "copy", "result": ["sir3"], "source": "__temp_lifted_3", "line": 21},
        ],
        "per_trial_steps": [],
    }

    # ACT
    try:
        actual_artifact = compile_valuascript(main_script, file_path=main_file_path, stop_after_stage="bytecode_ir_lowering")
        # Unwrap any _StringLiteral objects for comparison
        sir_args = actual_artifact["pre_trial_steps"][0]["args"]
        for i, arg in enumerate(sir_args):
            if hasattr(arg, "value"):
                sir_args[i] = arg.value

    except Exception as e:
        print(e)
        pytest.fail(f"Full pipeline compilation failed for a valid multi-return script: {e}")

    # ASSERT
    assert actual_artifact == expected_lowered_ir
