from vsc.bytecode_generation.opcodes import OpCode, OperandType

TEST_CASES = {
    "CompoundSerie": {
        "happy_path": {
            "args": "100, [0.05, 0.06, 0.07]",
            "expected_opcode": OpCode.CompoundSerie_V_SV,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 1, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [100.0], "VECTOR": [[0.05, 0.06, 0.07]], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 2,
            "srcs_types": [OperandType.SCALAR_CONST, OperandType.VECTOR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.VECTOR_REG],
        },
    },
    "GrowSerie": {
        "happy_path": {
            "args": "100, 0.05, 10",
            "expected_opcode": OpCode.GrowSerie_V_SSS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 1, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [100.0, 0.05, 10.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 3,
            "srcs_types": [OperandType.SCALAR_CONST, OperandType.SCALAR_CONST, OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.VECTOR_REG],
        },
    },
    "InterpolateSerie": {
        "happy_path": {
            "args": "10, 100, 10",
            "expected_opcode": OpCode.InterpolateSerie_V_SSS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 1, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [10.0, 100.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 3,
            "srcs_types": [OperandType.SCALAR_CONST, OperandType.SCALAR_CONST, OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.VECTOR_REG],
        },
    },
}
