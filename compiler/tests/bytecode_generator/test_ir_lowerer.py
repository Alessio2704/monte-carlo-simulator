import pytest
import json
from typing import Dict, Any, List

# The module we are testing
from vsc.bytecode_generation.ir_lowerer import IRLowerer
from vsc.optimizer.ir_validator import IRValidator

# --- Test Helpers ---


def pretty_format_ir(ir: Dict[str, Any]) -> str:
    """Helper to format IR for readable test failure messages."""
    return json.dumps(ir, indent=2)


@pytest.fixture
def base_registries() -> Dict[str, Any]:
    """Provides a clean, boilerplate registry object for tests."""
    return {
        "variable_registries": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []},
        "variable_map": {},
        "constant_pools": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []},
        "constant_map": {},
    }


def validate_ir(ir: List[Dict[str, Any]], pre_defined_vars: List[str] = None):
    """Helper to run the IR validator with optional pre-defined variables."""
    validator = IRValidator(ir)
    if pre_defined_vars:
        validator.defined_vars.update(pre_defined_vars)
    validator.validate()


# --- Comprehensive Test Suite for IRLowerer ---


def test_lowers_nested_conditional_assignments_correctly(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["tax_rate"])
    registries["variable_registries"]["BOOLEAN"].extend(["is_high_income", "is_medium_income"])
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
            {"type": "literal_assignment", "result": ["tax_rate"], "value": "__temp_lifted_1", "line": 59},
            {"type": "label", "name": "__end_label_3", "line": 59},
        ],
    }

    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()

    # ASSERT
    assert actual_result == final_expected_ir
    validate_ir(actual_result["per_trial_steps"], ["is_high_income", "is_medium_income"])


def test_lifts_simple_nested_function_call(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["x", "result"])
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
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()

    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["per_trial_steps"], ["x"])


def test_lifts_multiple_nested_calls_in_one_instruction(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["result"])
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
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["per_trial_steps"])


def test_lifts_deeply_nested_function_call(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["x", "y", "result"])
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
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["per_trial_steps"], ["x", "y"])


def test_lowers_identity_to_copy(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["a", "b"])
    partitioned_ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["a"], "function": "identity", "args": ["b"], "line": 10}], "per_trial_steps": []}
    expected_ir = {"pre_trial_steps": [{"type": "copy", "result": ["a"], "source": "b", "line": 10}], "per_trial_steps": []}
    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    validate_ir(actual_result["pre_trial_steps"], ["b"])


def test_counters_continue_across_partitions(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["BOOLEAN"].extend(["cond"])
    registries["variable_registries"]["SCALAR"].extend(["x"])
    partitioned_ir = {
        "pre_trial_steps": [{"type": "conditional_assignment", "result": ["x"], "condition": "cond", "then_expr": 1, "else_expr": 2, "line": 1}],
        "per_trial_steps": [{"type": "execution_assignment", "result": ["x"], "function": "add", "args": ["x", {"function": "Normal", "args": [0, 1]}], "line": 2}],
    }
    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()
    # ASSERT
    assert lowerer.label_counter == 2
    assert lowerer.temp_var_counter == 1
    validate_ir(actual_result["pre_trial_steps"], ["cond"])
    validate_ir(actual_result["per_trial_steps"], ["x"])  # x is defined in pre-trial


def test_handles_empty_ir_gracefully(base_registries):
    # ARRANGE
    partitioned_ir = {"pre_trial_steps": [], "per_trial_steps": []}
    # ACT
    lowerer = IRLowerer(partitioned_ir, base_registries, model={})
    actual_result = lowerer.lower()
    # ASSERT
    assert actual_result == partitioned_ir


def test_preserves_ir_with_no_lowerable_instructions(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["a", "b"])
    partitioned_ir = {
        "pre_trial_steps": [{"type": "literal_assignment", "result": ["a"], "value": 10, "line": 1}, {"type": "execution_assignment", "result": ["b"], "function": "add", "args": ["a", 5], "line": 2}],
        "per_trial_steps": [],
    }
    original_ir = json.loads(json.dumps(partitioned_ir))
    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()
    # ASSERT
    assert actual_result == original_ir
    validate_ir(actual_result["pre_trial_steps"])


def test_kitchen_sink_nested_conditional_with_nested_function(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["result"])
    registries["variable_registries"]["BOOLEAN"].extend(["is_critical", "use_stochastic"])
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
            {"type": "literal_assignment", "result": ["__temp_lifted_2"], "value": "__temp_lifted_1", "line": 40},
            {"type": "jump", "target": "__end_label_1", "line": 40},
            {"type": "label", "name": "__else_label_0", "line": 40},
            {"type": "literal_assignment", "result": ["__temp_lifted_2"], "value": 25, "line": 40},
            {"type": "label", "name": "__end_label_1", "line": 40},
            {"type": "jump_if_false", "condition": "is_critical", "target": "__else_label_2", "line": 40},
            {"type": "literal_assignment", "result": ["result"], "value": 100, "line": 40},
            {"type": "jump", "target": "__end_label_3", "line": 40},
            {"type": "label", "name": "__else_label_2", "line": 40},
            {"type": "literal_assignment", "result": ["result"], "value": "__temp_lifted_2", "line": 40},
            {"type": "label", "name": "__end_label_3", "line": 40},
        ],
    }
    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model={})
    actual_result = lowerer.lower()
    # ASSERT
    assert actual_result == full_expected
    validate_ir(actual_result["per_trial_steps"], ["is_critical", "use_stochastic"])


def test_lifts_function_call_from_condition(base_registries):
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["a", "result"])
    model = {"all_signatures": {"greater_than": {"return_type": "boolean"}}}
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
    lowerer = IRLowerer(partitioned_ir, registries, model)
    actual_result = lowerer.lower()
    # ASSERT
    assert actual_result == expected_ir
    assert registries["variable_map"]["__temp_lifted_1"]["type"] == "BOOLEAN"
    validate_ir(actual_result["pre_trial_steps"], ["a"])
