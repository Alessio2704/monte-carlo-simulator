from vsc.bytecode_generation.opcodes import OpCode, OperandType

TEST_CASES = {
    "ComposeVector": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 2, 3",
            "expected_opcode": OpCode.ComposeVector_V_SSS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 1, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [1.0, 2.0, 3.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 3,
            "srcs_types": [OperandType.SCALAR_CONST, OperandType.SCALAR_CONST, OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.VECTOR_REG],
        },
    },
    "SumVector": {
        "happy_path": {
            "assignment": "let x",
            "args": "[1, 2, 3]",
            "expected_opcode": OpCode.SumVector_S_V,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [], "VECTOR": [[1.0, 2.0, 3.0]], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.VECTOR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        },
    },
    "VectorDelta": {
        "happy_path": {
            "assignment": "let x",
            "args": "[1, 3, 6, 10]",
            "expected_opcode": OpCode.VectorDelta_V_V,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 1, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [], "VECTOR": [[1.0, 3.0, 6.0, 10.0]], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.VECTOR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.VECTOR_REG],
        },
    },
    "GetElement": {
        "happy_path": {
            "assignment": "let x",
            "args": "[10, 20, 30], 1",
            "expected_opcode": OpCode.GetElement_S_VS,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [1.0], "VECTOR": [[10.0, 20.0, 30.0]], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 2,
            "srcs_types": [OperandType.VECTOR_CONST, OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        },
    },
    "DeleteElement": {
        "happy_path": {
            "assignment": "let x",
            "args": "[10, 20, 30], 1",
            "expected_opcode": OpCode.DeleteElement_V_VS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 1, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [1.0], "VECTOR": [[10.0, 20.0, 30.0]], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 2,
            "srcs_types": [OperandType.VECTOR_CONST, OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.VECTOR_REG],
        },
    },
}
