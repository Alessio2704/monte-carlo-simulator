from vsc.bytecode_generation.opcodes import OpCode, OperandType


"""
Some functions do not have the "constants" key because they will be folded.
The constant resulting from the folding will likely have multiple decimal places making the assert probability fail due to precision.
"""

TEST_CASES = {
    "__eq__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 1",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__neq__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 2",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__gt__": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 1",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__lt__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 2",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__gte__": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 2",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__lte__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 1",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__and__": {
        "happy_path": {
            "assignment": "let x",
            "args": "true, false",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__or__": {
        "happy_path": {
            "assignment": "let x",
            "args": "true, false",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "__not__": {
        "happy_path": {
            "assignment": "let x",
            "args": "true",
            "expected_opcode": OpCode.copy_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
            "will_be_folded": True,
        }
    },
    "add": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 2",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
    "subtract": {
        "happy_path": {
            "assignment": "let x",
            "args": "3, 1",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
    "multiply": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 3",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
    "divide": {
        "happy_path": {
            "assignment": "let x",
            "args": "6, 3",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
    "power": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 3",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
    "identity": {
        "happy_path": {
            "assignment": "let x",
            "args": "123.45",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [123.45], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": False,
        }
    },
    "log": {
        "happy_path": {
            "assignment": "let x",
            "args": "10",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
    "log10": {
        "happy_path": {
            "assignment": "let x",
            "args": "100",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
    "exp": {
        "happy_path": {
            "assignment": "let x",
            "args": "2",
            "expected_opcode": OpCode.copy_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
            "will_be_folded": True,
        }
    },
}
