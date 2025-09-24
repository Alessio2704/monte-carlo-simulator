import pytest
from vsc.compiler import compile_valuascript
from vsc.bytecode_generation.opcodes import OpCode, OperandType
from tests.end_to_end.utils import _pack, load_script


def test_vector_add_chain_compiles_correctly():
    """
    Tests that a chain of vector additions is correctly lowered, optimized,
    and emitted as valid bytecode.
    """
    # 1. ARRANGE: Load the script and compile it to the final recipe
    script_content = load_script("tests/end_to_end/mixed_scalar_vector_subtract/mixed_scalar_vector_subtract.vs")
    recipe = compile_valuascript(script_content)

    # 2. ASSERT: Inspect the final recipe for correctness

    # --- Assert on the high-level configuration ---
    assert recipe["simulation_config"]["num_trials"] == 1
    assert recipe["simulation_config"]["output_variable"] == "z"
    assert recipe["variable_register_counts"]["VECTOR"] == 1
    assert len(recipe["constants"]["SCALAR"]) == 1
    assert len(recipe["constants"]["VECTOR"]) == 1

    assert len(recipe["per_trial_instructions"]) == 0

    pre_trial_ops = recipe["pre_trial_instructions"]

    assert len(pre_trial_ops) == 1

    final_instruction = pre_trial_ops[-1]

    assert len(final_instruction["dests"]) == 1
    assert len(final_instruction["srcs"]) == 2

    assert final_instruction["srcs"][0] == _pack(OperandType.VECTOR_CONST, 0)
    assert final_instruction["srcs"][1] == _pack(OperandType.SCALAR_CONST, 0)
    assert final_instruction["dests"][0] == _pack(OperandType.VECTOR_REG, 0)
    assert final_instruction["op"] == OpCode.subtract_V_VS.value
