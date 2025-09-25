from vsc.bytecode_generation.opcodes import OpCode, OperandType

# Note the name: TEST_CASES. This is the convention our aggregator will look for.
TEST_CASES = {
    "Npv": {
        "happy_path": {
            "assignment": "let x",
            "args": "0.05, [1,2,3]",
            "expected_opcode": OpCode.Npv_S_SV,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [0.05], "VECTOR": [[1.0, 2.0, 3.0]], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 2,
            "srcs_types": [OperandType.SCALAR_CONST, OperandType.VECTOR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        },
    },
    "CapitalizeExpenses": {
        "happy_path": {
            "assignment": "let x, y",
            "args": "100, [50, 60, 70], 5",
            "expected_opcode": OpCode.CapitalizeExpenses_SS_SVS,
            "variable_register_counts": {"SCALAR": 2, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [100.0, 5.0], "VECTOR": [[50.0, 60.0, 70.0]], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 3,
            "srcs_types": [OperandType.SCALAR_CONST, OperandType.VECTOR_CONST, OperandType.SCALAR_CONST],
            "dests_count": 2,
            "dests_types": [OperandType.SCALAR_REG, OperandType.SCALAR_REG],
        }
    },
    "BlackScholes": {
        "happy_path": {
            "assignment": "let x",
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
