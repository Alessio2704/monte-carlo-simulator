from vsc.bytecode_generation.opcodes import OpCode, OperandType


def load_script(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


# Helper to pack operands for easy comparison
def _pack(op_type: OperandType, index: int) -> int:
    return (op_type.value << 27) | index
