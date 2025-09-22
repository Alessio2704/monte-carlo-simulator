import pytest
import json
from typing import Dict, Any, List

# The module we are testing
from vsc.bytecode_generation.ir_lowerer import IRLowerer

# --- Test Helpers ---


def pretty_format_ir(ir: Dict[str, Any]) -> str:
    """Helper to format IR for readable test failure messages."""
    return json.dumps(ir, indent=2)


# --- The Failing Test for Nested Conditionals (TDD) ---


def test_lowers_nested_conditional_assignments_correctly():
    """
    Tests that the IRLowerer can handle a conditional_assignment where the
    'else_expr' is itself another conditional_expression.

    This is a critical test for ensuring the "lifting" phase correctly
    flattens all forms of nested logic before the control-flow lowering phase.
    """
    # --- 1. ARRANGE: Define the minimal input to reproduce the bug ---

    # The input is a single, nested conditional assignment.
    # let tax_rate = if is_high_income then 0.4 else (if is_medium_income then 0.3 else 0.2)
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

    # Define the minimal registries that ResourceAllocator would have created.
    registries = {
        "variable_registries": {
            "SCALAR": ["tax_rate"],
            "VECTOR": [],
            "BOOLEAN": ["is_high_income", "is_medium_income"],
            "STRING": [],
        },
        "variable_map": {
            "tax_rate": {"type": "SCALAR", "index": 0},
            "is_high_income": {"type": "BOOLEAN", "index": 0},
            "is_medium_income": {"type": "BOOLEAN", "index": 1},
        },
        "constant_pools": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []},
        "constant_map": {},
    }

    # The model is not strictly needed for this test but is part of the class signature.
    model = {}

    # --- 2. DEFINE EXPECTED OUTPUT: Manually trace the correct lowered IR ---
    # The expected behavior is that the nested conditional is "lifted" into a
    # temporary variable first, and then both conditionals are lowered to jumps.
    expected_lowered_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [
            # LIFTING PASS OUTPUT:
            # let __temp_lifted_1 = if is_medium_income then 0.3 else 0.2
            # let tax_rate = if is_high_income then 0.4 else __temp_lifted_1
            # FINAL LOWERED OUTPUT:
            # --- Start of the INNER conditional (lifted) ---
            {"type": "jump_if_false", "condition": "is_medium_income", "target": "__else_label_0", "line": 59},
            {"type": "literal_assignment", "result": ["__temp_lifted_1"], "value": 0.3, "line": 59},
            {"type": "jump", "target": "__end_label_1", "line": 59},
            {"type": "label", "name": "__else_label_0", "line": 59},
            {"type": "literal_assignment", "result": ["__temp_lifted_1"], "value": 0.2, "line": 59},
            {"type": "label", "name": "__end_label_1", "line": 59},
            # --- Start of the OUTER conditional ---
            {"type": "jump_if_false", "condition": "is_high_income", "target": "__else_label_2", "line": 59},
            {"type": "literal_assignment", "result": ["tax_rate"], "value": 0.4, "line": 59},
            {"type": "jump", "target": "__end_label_3", "line": 59},
            {"type": "label", "name": "__else_label_2", "line": 59},
            {"type": "literal_assignment", "result": ["tax_rate"], "value": "__temp_lifted_1", "line": 59},  # The result of the lifted conditional
            {"type": "label", "name": "__end_label_3", "line": 59},
        ],
    }

    # --- 3. ACT: Run the unit under test ---
    lowerer = IRLowerer(partitioned_ir, registries, model)
    actual_result = lowerer.lower()

    # --- 4. ASSERT: Check if the actual output matches the expected contract ---
    if actual_result != expected_lowered_ir:
        pytest.fail("The IRLowerer did not correctly lower the nested conditional.\n" f"EXPECTED:\n{pretty_format_ir(expected_lowered_ir)}\n\n" f"ACTUAL:\n{pretty_format_ir(actual_result)}")

    assert actual_result == expected_lowered_ir
