import pytest
from vsc.optimizer.alias_resolver import run_alias_resolver


def test_resolves_simple_alias_and_removes_identity():
    """
    Tests the primary use case: `let final = identity(__temp)` should be resolved.
    """
    unoptimized_ir = [
        # Step 0: The original calculation producing a temporary variable
        {"type": "execution_assignment", "result": ["__temp_d_tv"], "function": "calculate_tv", "args": []},
        # Step 1: Another instruction
        {"type": "literal_assignment", "result": ["another_var"], "value": 123},
        # Step 2: The identity call that creates the alias
        {"type": "execution_assignment", "result": ["d_tv"], "function": "identity", "args": ["__temp_d_tv"]},
    ]

    expected_ir = [
        # The original calculation now directly produces the final variable
        {"type": "execution_assignment", "result": ["d_tv"], "function": "calculate_tv", "args": []},
        # The other instruction is untouched
        {"type": "literal_assignment", "result": ["another_var"], "value": 123},
        # The identity instruction is gone
    ]

    optimized_ir = run_alias_resolver(unoptimized_ir)
    assert optimized_ir == expected_ir


def test_handles_no_opportunities():
    """Ensures the IR is unchanged if the aliasing pattern is not present."""
    ir = [
        {"type": "execution_assignment", "result": ["x"], "function": "add", "args": [1, 2]},
        {"type": "literal_assignment", "result": ["y"], "value": 10},
    ]
    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == ir
