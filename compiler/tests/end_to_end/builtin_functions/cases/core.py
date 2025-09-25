from vsc.bytecode_generation.opcodes import OpCode, OperandType
import math

TEST_CASES = {
    "__eq__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 1",
            "expected_opcode": OpCode.eq_B_SS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [1.0, 1.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__neq__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 2",
            "expected_opcode": OpCode.neq_B_SS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [1.0, 2.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__gt__": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 1",
            "expected_opcode": OpCode.gt_B_SS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [2.0, 1.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__lt__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 2",
            "expected_opcode": OpCode.lt_B_SS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [1.0, 2.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__gte__": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 2",
            "expected_opcode": OpCode.gte_B_SS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [2.0, 2.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__lte__": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 1",
            "expected_opcode": OpCode.lte_B_SS,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [1.0, 1.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__and__": {
        "happy_path": {
            "assignment": "let x",
            "args": "true, false",
            "expected_opcode": OpCode.and_B_BB,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [True, False], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__or__": {
        "happy_path": {
            "assignment": "let x",
            "args": "true, false",
            "expected_opcode": OpCode.or_B_BB,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [True, False], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "__not__": {
        "happy_path": {
            "assignment": "let x",
            "args": "true",
            "expected_opcode": OpCode.not_B_B,
            "variable_register_counts": {"SCALAR": 0, "VECTOR": 0, "BOOLEAN": 1, "STRING": 0},
            "constants": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [True], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.BOOLEAN_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.BOOLEAN_REG],
        }
    },
    "add": {
        "happy_path": {
            "assignment": "let x",
            "args": "1, 2",
            "expected_opcode": OpCode.add_S_SS,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [1.0, 2.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        }
    },
    "subtract": {
        "happy_path": {
            "assignment": "let x",
            "args": "3, 1",
            "expected_opcode": OpCode.subtract_S_SS,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [3.0, 1.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        }
    },
    "multiply": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 3",
            "expected_opcode": OpCode.multiply_S_SS,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [2.0, 3.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        }
    },
    "divide": {
        "happy_path": {
            "assignment": "let x",
            "args": "6, 3",
            "expected_opcode": OpCode.divide_S_SS,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [6.0, 3.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        }
    },
    "power": {
        "happy_path": {
            "assignment": "let x",
            "args": "2, 3",
            "expected_opcode": OpCode.power_S_SS,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [2.0, 3.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
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
            "expected_opcode": OpCode.log_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [10.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        }
    },
    "log10": {
        "happy_path": {
            "assignment": "let x",
            "args": "100",
            "expected_opcode": OpCode.log10_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [100.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        }
    },
    "exp": {
        "happy_path": {
            "assignment": "let x",
            "args": "2",
            "expected_opcode": OpCode.exp_S_S,
            "variable_register_counts": {"SCALAR": 1, "VECTOR": 0, "BOOLEAN": 0, "STRING": 0},
            "constants": {"SCALAR": [2.0], "VECTOR": [], "BOOLEAN": [], "STRING": []},
            "is_stochastic": False,
            "srcs_count": 1,
            "srcs_types": [OperandType.SCALAR_CONST],
            "dests_count": 1,
            "dests_types": [OperandType.SCALAR_REG],
        }
    },
}
