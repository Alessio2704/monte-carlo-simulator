from vsc.bytecode_generation.opcodes import OpCode, OperandType

# This dictionary is now the single source of truth for testing built-in functions.
# To add tests for a new function, you just add a new entry here.
BUILTIN_TEST_CASES = {
    "BlackScholes": {
        "happy_path": {
            "args": '100, 110, 0.05, 0.5, 0.2, "call"',
            "expected_opcode": OpCode.BlackScholes_S_SSSSSSTR,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [100.0, 110.0, 0.05, 0.5, 0.2], "VECTOR": [], "BOOLEAN": [], "STRING": ["call"]},
            "is_stochastic": False,
            "srcs_count": 6,
            "srcs_types": [OperandType.SCALAR_CONST, OperandType.SCALAR_CONST, OperandType.SCALAR_CONST, OperandType.SCALAR_CONST, OperandType.SCALAR_CONST, OperandType.STRING_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        },
    },
}
