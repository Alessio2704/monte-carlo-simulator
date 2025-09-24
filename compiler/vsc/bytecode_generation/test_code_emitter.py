import pytest
from typing import Dict, Any

# The module we are testing
from vsc.bytecode_generation.code_emitter import CodeEmitter
from vsc.bytecode_generation.opcodes import OpCode, OperandType
from vsc.parser import _StringLiteral

# --- Test Helpers & Fixtures ---


def _pack(op_type: OperandType, index: int) -> int:
    """Helper to consistently pack operands for test assertions."""
    return (op_type.value << 27) | index


@pytest.fixture
def base_registries() -> Dict[str, Any]:
    """Provides a standard set of registries for the emitter to use in tests."""
    return {
        "variable_map": {
            "s_var1": {"type": "SCALAR", "index": 0},
            "s_var2": {"type": "SCALAR", "index": 1},
            "v_var1": {"type": "VECTOR", "index": 0},
            "b_var1": {"type": "BOOLEAN", "index": 0},
            "b_var2": {"type": "BOOLEAN", "index": 1},
            "str_var1": {"type": "STRING", "index": 0},
        },
        "constant_map": {
            "s_100.0": {"type": "SCALAR", "index": 0},
            "s_50.0": {"type": "SCALAR", "index": 1},
            "v_s_1.0_s_2.0": {"type": "VECTOR", "index": 0},
            "b_true": {"type": "BOOLEAN", "index": 0},
            "str_hello": {"type": "STRING", "index": 0},
        },
    }


# --- Test Suite ---


def test_emits_simple_binary_operation(base_registries):
    """
    Tests emission of a standard execution_assignment with one register and one constant source.
    """
    # ARRANGE
    lowered_ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["s_var2"], "function": "add", "args": ["s_var1", 100.0]}], "per_trial_steps": []}
    expected_bytecode = {
        "pre_trial_instructions": [
            {"op": OpCode.add_S_SS.value, "dests": [_pack(OperandType.SCALAR_REG, 1)], "srcs": [_pack(OperandType.SCALAR_REG, 0), _pack(OperandType.SCALAR_CONST, 0)]}  # s_var2  # s_var1, 100.0
        ],
        "per_trial_instructions": [],
    }

    # ACT
    emitter = CodeEmitter(lowered_ir, base_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode


def test_emits_multi_return_function_call(base_registries):
    """
    Tests emission of an instruction with multiple destinations.
    """
    # ARRANGE
    lowered_ir = {"per_trial_steps": [{"type": "execution_assignment", "result": ["s_var1", "s_var2"], "function": "CapitalizeExpenses", "args": [100.0, "v_var1", 50.0]}], "pre_trial_steps": []}
    expected_bytecode = {
        "per_trial_instructions": [
            {
                "op": OpCode.CapitalizeExpenses_SS_SVS.value,
                "dests": [_pack(OperandType.SCALAR_REG, 0), _pack(OperandType.SCALAR_REG, 1)],  # s_var1, s_var2
                "srcs": [_pack(OperandType.SCALAR_CONST, 0), _pack(OperandType.VECTOR_REG, 0), _pack(OperandType.SCALAR_CONST, 1)],  # 100.0, v_var1, 50.0
            }
        ],
        "pre_trial_instructions": [],
    }

    # ACT
    emitter = CodeEmitter(lowered_ir, base_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode


def test_emits_data_movement_and_literal_assignment(base_registries):
    """
    Tests both `copy` from a register and `literal_assignment` which becomes a copy from a constant.
    """
    # ARRANGE
    lowered_ir = {
        "pre_trial_steps": [{"type": "copy", "result": ["s_var1"], "source": "s_var2"}, {"type": "literal_assignment", "result": ["str_var1"], "value": _StringLiteral("hello")}],
        "per_trial_steps": [],
    }
    expected_bytecode = {
        "pre_trial_instructions": [
            {"op": OpCode.copy_S_S.value, "dests": [_pack(OperandType.SCALAR_REG, 0)], "srcs": [_pack(OperandType.SCALAR_REG, 1)]},  # s_var1  # s_var2
            {"op": OpCode.copy_STR_STR.value, "dests": [_pack(OperandType.STRING_REG, 0)], "srcs": [_pack(OperandType.STRING_CONST, 0)]},  # str_var1  # "hello"
        ],
        "per_trial_instructions": [],
    }

    # ACT
    emitter = CodeEmitter(lowered_ir, base_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode


def test_emits_control_flow_instructions(base_registries):
    """
    Tests emission of JUMP and JUMP_IF_FALSE by providing the full IR with labels
    and letting the emitter's internal linking phase handle it.
    """
    # ARRANGE
    # This IR now includes the label instructions, which is the correct input format.
    lowered_ir = {
        "pre_trial_steps": [
            {"type": "jump_if_false", "condition": "b_var1", "target": "__else_label_0"},
            {"type": "copy", "result": ["s_var1"], "source": "s_var2"},  # Executable instruction at Address 1
            {"type": "jump", "target": "__end_label_1"},
            {"type": "label", "name": "__else_label_0"},
            {"type": "copy", "result": ["s_var2"], "source": "s_var1"},  # Executable instruction at Address 3
            {"type": "label", "name": "__end_label_1"},
        ],
        "per_trial_steps": [],
    }

    expected_bytecode = {
        "pre_trial_instructions": [
            # The JUMP_IF_FALSE should target address 3 (the instruction after the label).
            {"op": OpCode.JUMP_IF_FALSE.value, "dests": [], "srcs": [_pack(OperandType.BOOLEAN_REG, 0), 3]},
            {"op": OpCode.copy_S_S.value, "dests": [_pack(OperandType.SCALAR_REG, 0)], "srcs": [_pack(OperandType.SCALAR_REG, 1)]},
            # The JUMP should target address 4 (the end of the executable block).
            {"op": OpCode.JUMP.value, "dests": [], "srcs": [4]},
            {"op": OpCode.copy_S_S.value, "dests": [_pack(OperandType.SCALAR_REG, 1)], "srcs": [_pack(OperandType.SCALAR_REG, 0)]},
        ],
        "per_trial_instructions": [],
    }

    # ACT
    emitter = CodeEmitter(lowered_ir, base_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode


def test_emits_sanitized_operator_names(base_registries):
    """
    Tests that internal operator names like '__eq__' are correctly sanitized before opcode lookup.
    """
    # ARRANGE
    lowered_ir = {"per_trial_steps": [{"type": "execution_assignment", "result": ["b_var2"], "function": "__eq__", "args": ["s_var1", 100.0]}], "pre_trial_steps": []}
    expected_bytecode = {
        "per_trial_instructions": [
            {
                "op": OpCode.eq_B_SS.value,  # Correctly resolves to 'eq_B_SS', not '__eq___B_SS'
                "dests": [_pack(OperandType.BOOLEAN_REG, 1)],  # b_var2
                "srcs": [_pack(OperandType.SCALAR_REG, 0), _pack(OperandType.SCALAR_CONST, 0)],  # s_var1, 100.0
            }
        ],
        "pre_trial_instructions": [],
    }

    # ACT
    emitter = CodeEmitter(lowered_ir, base_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode


def test_handles_empty_partitions_gracefully(base_registries):
    """
    Ensures that an empty IR produces an empty bytecode artifact without errors.
    """
    # ARRANGE
    lowered_ir = {"pre_trial_steps": [], "per_trial_steps": []}
    expected_bytecode = {"pre_trial_instructions": [], "per_trial_instructions": []}

    # ACT
    emitter = CodeEmitter(lowered_ir, base_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode
