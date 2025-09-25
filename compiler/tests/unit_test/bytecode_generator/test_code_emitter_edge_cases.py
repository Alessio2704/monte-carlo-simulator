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
def extended_registries() -> Dict[str, Any]:
    """
    Provides a more comprehensive set of registries for complex edge-case tests.
    """
    return {
        "variable_map": {
            "spot": {"type": "SCALAR", "index": 0},
            "strike": {"type": "SCALAR", "index": 1},
            "result_scalar": {"type": "SCALAR", "index": 2},
            "b_var": {"type": "BOOLEAN", "index": 0},
        },
        "constant_map": {
            "s_0.05": {"type": "SCALAR", "index": 0},
            "s_1.0": {"type": "SCALAR", "index": 1},
            "s_0.2": {"type": "SCALAR", "index": 2},
            "str_call": {"type": "STRING", "index": 0},
        },
    }


# --- Edge Case Test Suite ---


def test_emits_complex_multi_type_function_call(extended_registries):
    """
    Tests a complex "kitchen sink" instruction with multiple sources of
    different types (scalar registers, scalar constants, string constant).
    """
    # ARRANGE
    lowered_ir = {
        "pre_trial_steps": [],
        "per_trial_steps": [{"type": "execution_assignment", "result": ["result_scalar"], "function": "BlackScholes", "args": ["spot", "strike", 0.05, 1.0, 0.2, _StringLiteral("call")], "line": 50}],
    }
    expected_bytecode = {
        "pre_trial_instructions": [],
        "per_trial_instructions": [
            {
                "op": OpCode.BlackScholes_S_SSSSSSTR.value,
                "dests": [_pack(OperandType.SCALAR_REG, 2)],
                "srcs": [
                    _pack(OperandType.SCALAR_REG, 0),
                    _pack(OperandType.SCALAR_REG, 1),
                    _pack(OperandType.SCALAR_CONST, 0),
                    _pack(OperandType.SCALAR_CONST, 1),
                    _pack(OperandType.SCALAR_CONST, 2),
                    _pack(OperandType.STRING_CONST, 0),
                ],
                "line": 50,
            }
        ],
    }

    # ACT
    emitter = CodeEmitter(lowered_ir, extended_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode


def test_emits_zero_argument_function_call(extended_registries, monkeypatch):
    """
    Tests an instruction that has a destination but no source operands.
    This uses monkeypatch to simulate the existence of a zero-arg opcode.
    """

    # ARRANGE
    class MockOpCodeMember:
        value = 999

    monkeypatch.setitem(OpCode._member_map_, "get_pi_S_", MockOpCodeMember)

    lowered_ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["result_scalar"], "function": "get_pi", "args": [], "line": 60}], "per_trial_steps": []}
    expected_bytecode = {"pre_trial_instructions": [{"op": 999, "dests": [_pack(OperandType.SCALAR_REG, 2)], "srcs": [], "line": 60}], "per_trial_instructions": []}

    # ACT
    emitter = CodeEmitter(lowered_ir, extended_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode


def test_emits_both_partitions_correctly_and_independently(extended_registries):
    """
    Tests that the emitter processes both pre-trial and per-trial partitions
    in a single run, and that the linking phase of one does not affect the other.
    """
    # ARRANGE
    lowered_ir = {
        "pre_trial_steps": [{"type": "execution_assignment", "result": ["result_scalar"], "function": "add", "args": ["spot", 1.0], "line": 70}],
        "per_trial_steps": [
            {"type": "jump_if_false", "condition": "b_var", "target": "__per_trial_label", "line": 80},
            {"type": "execution_assignment", "result": ["strike"], "function": "add", "args": ["strike", 1.0], "line": 81},
            {"type": "label", "name": "__per_trial_label", "line": 82},
        ],
    }
    expected_bytecode = {
        "pre_trial_instructions": [
            {"op": OpCode.add_S_SS.value, "dests": [_pack(OperandType.SCALAR_REG, 2)], "srcs": [_pack(OperandType.SCALAR_REG, 0), _pack(OperandType.SCALAR_CONST, 1)], "line": 70}
        ],
        "per_trial_instructions": [
            {"op": OpCode.JUMP_IF_FALSE.value, "dests": [], "srcs": [_pack(OperandType.BOOLEAN_REG, 0), 2], "line": 80},
            {"op": OpCode.add_S_SS.value, "dests": [_pack(OperandType.SCALAR_REG, 1)], "srcs": [_pack(OperandType.SCALAR_REG, 1), _pack(OperandType.SCALAR_CONST, 1)], "line": 81},
        ],
    }

    # ACT
    emitter = CodeEmitter(lowered_ir, extended_registries)
    actual_bytecode = emitter.emit()

    # ASSERT
    assert actual_bytecode == expected_bytecode
