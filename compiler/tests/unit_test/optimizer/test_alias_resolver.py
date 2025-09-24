import pytest
from vsc.optimizer.alias_resolver import run_alias_resolver

# --- 1. Tests for Direct Aliasing (`identity(variable)`) ---


def assert_ir_equals_unordered(ir1, ir2):
    """
    Asserts that two IR lists are semantically equal, ignoring the order
    of instructions. It does this by sorting both lists based on a
    canonical representation of each instruction.
    """
    assert len(ir1) == len(ir2), "IR lists have different lengths"

    # Sort both lists of dictionaries based on their string representation for a stable sort
    sorted_ir1 = sorted(ir1, key=lambda x: str(x))
    sorted_ir2 = sorted(ir2, key=lambda x: str(x))

    assert sorted_ir1 == sorted_ir2


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


def test_handles_no_direct_alias_opportunities():
    """Ensures the IR is unchanged if the direct aliasing pattern is not present."""
    ir = [
        {"type": "execution_assignment", "result": ["x"], "function": "add", "args": [1, 2]},
        {"type": "literal_assignment", "result": ["y"], "value": 10},
    ]
    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == ir


# --- 2. Migrated Tests for Expression Aliasing (`identity(expression)`) ---


def test_resolves_expression_alias_from_nested_function():
    """
    MIGRATED: Formerly test_eliminates_identity_wrapper_from_udf_return.
    Tests that `let z = identity(add(a, b))` is simplified.
    """
    ir = [{"type": "execution_assignment", "result": ["z"], "function": "identity", "args": [{"function": "add", "args": ["a", "b"]}], "line": 5}]

    expected_ir = [{"type": "execution_assignment", "result": ["z"], "function": "add", "args": ["a", "b"], "line": 5}]

    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == expected_ir


def test_resolves_expression_alias_from_nested_builtin():
    """
    MIGRATED: Formerly test_eliminates_identity_on_builtin_call.
    Tests that `let z = identity(Normal(0, 1))` is simplified.
    """
    ir = [{"type": "execution_assignment", "result": ["z"], "function": "identity", "args": [{"function": "Normal", "args": [0, 1]}], "line": 6}]

    expected_ir = [{"type": "execution_assignment", "result": ["z"], "function": "Normal", "args": [0, 1], "line": 6}]

    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == expected_ir


# --- 3. Negative Tests (What Not To Do) ---


def test_does_not_resolve_identity_wrapping_literal():
    """
    MIGRATED: Ensures the resolver does NOT touch `identity(5)`.
    This is the job of the ConstantFolder.
    """
    ir = [{"type": "execution_assignment", "result": ["x"], "function": "identity", "args": [5], "line": 4}]
    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == ir


def test_does_not_affect_tuple_identity():
    """
    Ensures the resolver does NOT touch `identity([a, b])`.
    This is the job of the TupleForwarder.
    """
    ir = [{"type": "execution_assignment", "result": ["x", "y"], "function": "identity", "args": [["a", "b"]], "line": 8}]
    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == ir


# --- 4. Advanced and Chained Scenarios ---


def test_resolves_chained_aliases(tmp_path):
    ir = [
        {"type": "literal_assignment", "result": ["a"], "value": 10},
        {"type": "execution_assignment", "result": ["b"], "function": "identity", "args": ["a"]},
        {"type": "execution_assignment", "result": ["c"], "function": "identity", "args": ["b"]},
    ]
    expected_ir = [
        {"type": "literal_assignment", "result": ["c"], "value": 10},
    ]
    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == expected_ir


def test_handles_multiple_independent_aliases(tmp_path):
    """
    Tests that multiple, unrelated alias chains in the same IR are all
    resolved correctly.
    """
    ir = [
        {"type": "literal_assignment", "result": ["a1"], "value": 1},
        {"type": "execution_assignment", "result": ["a2"], "function": "identity", "args": ["a1"]},
        {"type": "execution_assignment", "result": ["b1"], "function": "get_data", "args": []},
        {"type": "execution_assignment", "result": ["b2"], "function": "identity", "args": ["b1"]},
    ]
    expected_ir = [
        {"type": "literal_assignment", "result": ["a2"], "value": 1},
        {"type": "execution_assignment", "result": ["b2"], "function": "get_data", "args": []},
    ]
    optimized_ir = run_alias_resolver(ir)

    # Use the new helper for a robust, order-independent comparison
    assert_ir_equals_unordered(optimized_ir, expected_ir)


def test_resolves_alias_of_multi_assignment_result():
    ir = [
        {"type": "execution_assignment", "result": ["a", "b"], "function": "get_pair", "args": []},
        {"type": "execution_assignment", "result": ["my_final_a"], "function": "identity", "args": ["a"]},
    ]
    expected_ir = ir
    optimized_ir = run_alias_resolver(ir)
    assert optimized_ir == expected_ir
