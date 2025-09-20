import pytest
from pathlib import Path
from textwrap import dedent

# --- Test Dependencies ---
from vsc.optimizer.tuple_forwarding import run_tuple_forwarding

# --- Test Case ---


def test_forwards_tuple_assignment_and_eliminates_identity():
    """
    Tests the primary use case: a multi-return from a UDF is assigned
    to temps, which are then assigned to final variables via a redundant
    identity call. The pass should forward the results and remove the identity.
    """
    # This is the IR *before* our new optimization pass runs.
    # It simulates the state of the IR after IR generation.
    unoptimized_ir = [
        {
            "type": "execution_assignment",
            "result": ["__get_rd_1__capitalized_assets", "__get_rd_1__amortization_current_year"],
            "function": "capitalize_expense",
            "args": [52927, [49326, 45427, 39500], 3],
            "line": 52,
        },
        {
            "type": "execution_assignment",
            "result": ["value_of_research_assets", "current_year_amortization"],
            "function": "identity",
            "args": [["__get_rd_1__capitalized_assets", "__get_rd_1__amortization_current_year"]],
            "line": 10,
        },
        # Add another instruction to ensure it's not affected
        {"type": "execution_assignment", "result": ["something_else"], "function": "add", "args": ["value_of_research_assets", 1000]},
    ]

    # This is what we EXPECT the IR to look like *after* optimization.
    expected_ir = [
        {
            "type": "execution_assignment",
            # The result is now forwarded directly to the final variables.
            "result": ["value_of_research_assets", "current_year_amortization"],
            "function": "capitalize_expense",
            "args": [52927, [49326, 45427, 39500], 3],
            "line": 52,
        },
        # The redundant identity instruction has been eliminated.
        {"type": "execution_assignment", "result": ["something_else"], "function": "add", "args": ["value_of_research_assets", 1000]},
    ]

    # Run the (currently dummy) optimization pass
    optimized_ir = run_tuple_forwarding(unoptimized_ir)

    assert optimized_ir == expected_ir
