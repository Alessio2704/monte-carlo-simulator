from vsc.bytecode_generation.opcodes import OpCode, OperandType

TEST_CASES = {
    "ReadCsvScalar": {
        "happy_path": {
            "assignment": "let x",
            "args": '"./data.csv", "Value", 5',
            "expected_opcode": OpCode.ReadCsvScalar_S_STRSTRS,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [5.0], "VECTOR": [], "BOOLEAN": [], "STRING": ["./data.csv", "Value"]},
            "is_stochastic": False,
            "srcs_count": 3,
            "srcs_types": [OperandType.STRING_CONST, OperandType.STRING_CONST, OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        },
    },
    "ReadCsvVector": {
        "happy_path": {
            "assignment": "let x",
            "args": '"./data.csv", "ValueColumn"',
            "expected_opcode": OpCode.ReadCsvVector_V_STRSTR,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 1, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": ["./data.csv", "ValueColumn"]},
            "is_stochastic": False,
            "srcs_count": 2,
            "srcs_types": [OperandType.STRING_CONST, OperandType.STRING_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.VECTOR_REG],
        },
    },
}
