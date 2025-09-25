from vsc.bytecode_generation.opcodes import OpCode, OperandType

TEST_CASES = {
    "SirModel": {
        "happy_path": {
            "assignment": "let x, y, z",
            "args": "1000, 1, 0, 0.3, 0.1, 100, 1.0",
            "expected_opcode": OpCode.SirModel_VVV_SSSSSSS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 3, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [1000.0, 1.0, 0.0, 0.3, 0.1, 100.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 7,
            "srcs_types": [
                OperandType.SCALAR_CONST,
                OperandType.SCALAR_CONST,
                OperandType.SCALAR_CONST,
                OperandType.SCALAR_CONST,
                OperandType.SCALAR_CONST,
                OperandType.SCALAR_CONST,
                OperandType.SCALAR_CONST,
            ],
            "dests_count": 3,
            "dests_types": [OperandType.VECTOR_REG, OperandType.VECTOR_REG, OperandType.VECTOR_REG],
        },
    },
}
