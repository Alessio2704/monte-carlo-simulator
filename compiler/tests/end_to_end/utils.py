from vsc.bytecode_generation.opcodes import OpCode, OperandType


def load_script(path: str) -> str:
    with open(path, "r") as f:
        return f.read()


# Helper to pack operands for easy comparison
def _pack_operand(op_type: OperandType, index: int) -> int:
    return (op_type.value << 27) | index


# --- Helper to unpack an operand for type checking ---
def _unpack_operand(operand: int) -> OperandType:
    """Extracts the OperandType from a packed integer operand."""
    return OperandType(operand >> 27)
