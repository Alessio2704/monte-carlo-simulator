import pytest
import json
from typing import Dict, Any, List

# The module we are testing
from vsc.bytecode_generation.ir_lowerer import IRLowerer

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


# --- Comprehensive Test Suite for IRLowerer ---


def test_lowers_nested_conditional_assignments_correctly(base_registries):
    """
    Tests that the IRLowerer can handle a conditional_assignment where the
    'else_expr' is itself another conditional_expression. This is the original
    TDD test case, now serving as a high-level regression test.
    """
    # ARRANGE
    partitioned_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            {
                "type": "conditional_assignment",
                "result": ["tax_rate"],
                "condition": "is_high_income",
                "then_expr": 0.4,
                "else_expr": {
                    "type": "conditional_expression",
                    "condition": "is_medium_income",
                    "then_expr": 0.3,
                    "else_expr": 0.2,
                },
                "line": 59,
            }
        ],
    }
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["tax_rate"])
    registries["variable_registries"]["BOOLEAN"].extend(["is_high_income", "is_medium_income"])

    # This test is complex. Let's trace the full lowering AFTER lifting.
    final_expected_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            # Lowering of the inner conditional (which gets lifted first)
            {"type": "jump_if_false", "condition": "is_medium_income", "target": "__else_label_0", "line": 59},
            {"type": "literal_assignment", "result": ["__temp_lifted_1"], "value": 0.3, "line": 59},
            {"type": "jump", "target": "__end_label_1", "line": 59},
            {"type": "label", "name": "__else_label_0", "line": 59},
            {"type": "literal_assignment", "result": ["__temp_lifted_1"], "value": 0.2, "line": 59},
            {"type": "label", "name": "__end_label_1", "line": 59},
            # Lowering of the outer conditional
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
    assert "__temp_lifted_1" in registries["variable_registries"]["SCALAR"]


def test_lifts_simple_nested_function_call(base_registries):
    """Verifies the most basic lifting scenario: add(x, Normal(0, 1))"""
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
    assert "__temp_lifted_1" in registries["variable_map"]
    assert registries["variable_map"]["__temp_lifted_1"]["type"] == "SCALAR"


def test_lifts_multiple_nested_calls_in_one_instruction(base_registries):
    """Tests add(Normal(0,1), Normal(5,2)) to ensure correct order and multiple temp vars."""
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
    assert "__temp_lifted_1" in registries["variable_map"]
    assert "__temp_lifted_2" in registries["variable_map"]


def test_lifts_deeply_nested_function_call(base_registries):
    """Tests add(x, multiply(y, Normal(0,1))) to ensure recursive lifting works."""
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
    assert "__temp_lifted_1" in registries["variable_map"]
    assert "__temp_lifted_2" in registries["variable_map"]


def test_lowers_identity_to_copy(base_registries):
    """Tests that a simple identity() call is lowered to a 'copy' instruction."""
    # ARRANGE
    partitioned_ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["a"], "function": "identity", "args": ["b"], "line": 10}], "per_trial_steps": []}
    expected_ir = {"pre_trial_steps": [{"type": "copy", "result": ["a"], "source": "b", "line": 10}], "per_trial_steps": []}

    # ACT
    lowerer = IRLowerer(partitioned_ir, base_registries, model={})
    actual_result = lowerer.lower()

    # ASSERT
    assert actual_result == expected_ir


def test_counters_continue_across_partitions(base_registries):
    """Ensures temp var and label counters are not reset between partitions."""
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
    pre_trial_str = json.dumps(actual_result["pre_trial_steps"])
    per_trial_str = json.dumps(actual_result["per_trial_steps"])

    # Pre-trial should use the first set of labels (0, 1)
    assert "__else_label_0" in pre_trial_str
    assert "__end_label_1" in pre_trial_str

    # Per-trial should use the first temp var (1)
    assert "__temp_lifted_1" in per_trial_str

    # The label counter should have advanced for the next conditional
    assert lowerer.label_counter == 2
    assert lowerer.temp_var_counter == 1


def test_handles_empty_ir_gracefully(base_registries):
    """Tests that an empty IR is handled without errors."""
    # ARRANGE
    partitioned_ir = {"pre_trial_steps": [], "per_trial_steps": []}

    # ACT
    lowerer = IRLowerer(partitioned_ir, base_registries, model={})
    actual_result = lowerer.lower()

    # ASSERT
    assert actual_result == partitioned_ir


def test_preserves_ir_with_no_lowerable_instructions(base_registries):
    """Tests that an already-flat IR passes through unchanged."""
    # ARRANGE
    partitioned_ir = {
        "pre_trial_steps": [{"type": "literal_assignment", "result": ["a"], "value": 10, "line": 1}, {"type": "execution_assignment", "result": ["b"], "function": "add", "args": ["a", 5], "line": 2}],
        "per_trial_steps": [],
    }
    # Create a copy for comparison
    original_ir = json.loads(json.dumps(partitioned_ir))

    # ACT
    lowerer = IRLowerer(partitioned_ir, base_registries, model={})
    actual_result = lowerer.lower()

    # ASSERT
    assert actual_result == original_ir


def test_kitchen_sink_nested_conditional_with_nested_function(base_registries):
    """
    Tests the interaction of lifting a function call from within a nested
    conditional expression, ensuring correct flattening and lowering order.
    Scenario: `if is_critical then 100 else (if stochastic then Normal(50,5) else 25)`
    """
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

    # This is the ACTUALLY correct output after the two-phase process.
    # Phase 1 (Flattening) will produce an intermediate list of 3 instructions.
    # Phase 2 (Lowering) will process that list.
    full_expected = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            # The lifted `Normal` call from the innermost expression.
            {"type": "execution_assignment", "result": ["__temp_lifted_1"], "function": "Normal", "args": [50, 5], "line": 40},
            # The lowered sequence for the inner conditional, which now uses the temp var.
            # let __temp_lifted_2 = if use_stochastic then __temp_lifted_1 else 25
            {"type": "jump_if_false", "condition": "use_stochastic", "target": "__else_label_0", "line": 40},
            {"type": "literal_assignment", "result": ["__temp_lifted_2"], "value": "__temp_lifted_1", "line": 40},
            {"type": "jump", "target": "__end_label_1", "line": 40},
            {"type": "label", "name": "__else_label_0", "line": 40},
            {"type": "literal_assignment", "result": ["__temp_lifted_2"], "value": 25, "line": 40},
            {"type": "label", "name": "__end_label_1", "line": 40},
            # The lowered sequence for the outer conditional, which uses the result of the inner one.
            # let result = if is_critical then 100 else __temp_lifted_2
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
    assert "__temp_lifted_1" in registries["variable_map"]
    assert "__temp_lifted_2" in registries["variable_map"]
