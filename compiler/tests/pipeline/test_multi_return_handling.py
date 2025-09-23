import pytest
from textwrap import dedent
import json

from vsc.compiler import compile_valuascript


def create_dummy_file(tmp_path, filename, content):
    """Helper to create a temporary file for testing imports."""
    path = tmp_path / filename
    path.write_text(dedent(content).strip())
    return str(path)


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

    # Define the expected final, lowered IR structure with CORRECT types and line numbers
    expected_lowered_ir = {
        "pre_trial_steps": [
            {
                "type": "execution_assignment",
                "result": ["__temp_lifted_1", "__temp_lifted_2", "__temp_lifted_3"],
                "function": "SirModel",
                "args": [999990, 10, 0, 0.35, 0.07142857142857142, 120, 1.0],
                "line": 21,
            },
            {"type": "copy", "result": ["sir1", "sir2", "sir3"], "source": ["__temp_lifted_1", "__temp_lifted_2", "__temp_lifted_3"], "line": 21},  # Correct line number
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
        pytest.fail(f"Full pipeline compilation failed for a valid multi-return script: {e}")

    # ASSERT
    assert actual_artifact == expected_lowered_ir
