import pytest
from vsc.compiler import compile_valuascript
from vsc.bytecode_generation.opcodes import OpCode, OperandType
from tests.end_to_end.utils import _pack, load_script
from vsc.exceptions import ValuaScriptError, ErrorCode


def test_black_sholes():
    """
    Tests that a chain of vector additions is correctly lowered, optimized,
    and emitted as valid bytecode.
    """
    # 1. ARRANGE: Load the script and compile it to the final recipe
    script_content = load_script("tests/end_to_end/builtin/financial/black_sholes/black_sholes.vs")
    recipe = compile_valuascript(script_content)

    # 2. ASSERT: Inspect the final recipe for correctness

    # --- Assert on the high-level configuration ---
    assert recipe["simulation_config"]["num_trials"] == 1
    assert recipe["simulation_config"]["output_variable"] == "z"
    assert recipe["variable_register_counts"]["VECTOR"] == 0
    assert recipe["variable_register_counts"]["SCALAR"] == 1
    assert len(recipe["constants"]["VECTOR"]) == 0
    assert len(recipe["constants"]["SCALAR"]) == 5
    assert recipe["constants"]["SCALAR"] == [100, 110, 0.05, 0.5, 0.2]
    assert len(recipe["constants"]["STRING"]) == 1

    assert len(recipe["per_trial_instructions"]) == 0

    pre_trial_ops = recipe["pre_trial_instructions"]

    assert len(pre_trial_ops) == 1

    final_instruction = pre_trial_ops[-1]

    assert len(final_instruction["dests"]) == 1
    assert len(final_instruction["srcs"]) == 6

    assert final_instruction["srcs"][0] == _pack(OperandType.SCALAR_CONST, 0)
    assert final_instruction["srcs"][1] == _pack(OperandType.SCALAR_CONST, 1)
    assert final_instruction["srcs"][2] == _pack(OperandType.SCALAR_CONST, 2)
    assert final_instruction["srcs"][3] == _pack(OperandType.SCALAR_CONST, 3)
    assert final_instruction["srcs"][4] == _pack(OperandType.SCALAR_CONST, 4)
    assert final_instruction["srcs"][5] == _pack(OperandType.STRING_CONST, 0)
    assert final_instruction["dests"][0] == _pack(OperandType.SCALAR_REG, 0)
    assert final_instruction["op"] == OpCode.BlackScholes_S_SSSSSSTR.value


def test_black_sholes_arg_type_mismatch():

    script_content = load_script("tests/end_to_end/builtin/financial/black_sholes/black_sholes_arg_mis.vs")

    with pytest.raises(ValuaScriptError) as excinfo:
        compile_valuascript(script_content)

    assert excinfo.value.code == ErrorCode.ARGUMENT_TYPE_MISMATCH


def test_black_sholes_arg_num_mismatch():

    script_content = load_script("tests/end_to_end/builtin/financial/black_sholes/black_sholes_arg_num_mis.vs")

    with pytest.raises(ValuaScriptError) as excinfo:
        compile_valuascript(script_content)

    assert excinfo.value.code == ErrorCode.ARGUMENT_COUNT_MISMATCH


def test_black_sholes_stochastic_input_is_per_trial():

    script_content = load_script("tests/end_to_end/builtin/financial/black_sholes/black_sholes_stochastic.vs")
    recipe = compile_valuascript(script_content)

    # 1. The pre-trial block should now be EMPTY, as the optimizer will see
    #    that `random_spot` is only used by a per-trial instruction.
    assert len(recipe["pre_trial_instructions"]) == 0

    # 2. The per-trial block should contain the logic.
    #    It will have the Normal() call and the BlackScholes() call.
    assert len(recipe["per_trial_instructions"]) == 2

    # 3. The final instruction MUST be the BlackScholes call.
    final_instruction = recipe["per_trial_instructions"][-1]
    assert final_instruction["op"] == OpCode.BlackScholes_S_SSSSSSTR.value
