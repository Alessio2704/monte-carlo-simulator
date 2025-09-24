from typing import Dict, Any, List
from ..parser import _StringLiteral
from .opcodes import OpCode, OperandType


class CodeEmitter:
    """
    Implements Phase 8c of the bytecode pipeline.

    Performs a direct, mechanical translation of the fully lowered IR from
    Phase 8a into the final, integer-based instruction format, using the
    resource registries from Phase 8b for address lookups.
    """

    def __init__(self, lowered_ir: Dict[str, Any], registries: Dict[str, Any]):
        self.lowered_ir = lowered_ir
        self.registries = registries
        self.variable_map = registries.get("variable_map", {})
        self.constant_map = registries.get("constant_map", {})
        self.type_char_map = {"SCALAR": "S", "VECTOR": "V", "BOOLEAN": "B", "STRING": "STR"}

    def emit(self) -> Dict[str, List[Dict[str, Any]]]:
        """Orchestrates the two-phase "Link and Emit" process for both partitions."""
        pre_trial_bytecode = self._emit_partition(self.lowered_ir.get("pre_trial_steps", []))
        per_trial_bytecode = self._emit_partition(self.lowered_ir.get("per_trial_steps", []))
        return {
            "pre_trial_instructions": pre_trial_bytecode,
            "per_trial_instructions": per_trial_bytecode,
        }

    def _emit_partition(self, ir_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Runs the full Link and Emit algorithm for a single list of IR steps."""
        label_map: Dict[str, int] = {}
        final_ir: List[Dict[str, Any]] = []
        final_address_counter = 0
        for instruction in ir_steps:
            if instruction.get("type") == "label":
                label_map[instruction["name"]] = final_address_counter
            else:
                final_ir.append(instruction)
                final_address_counter += 1

        bytecode: List[Dict[str, Any]] = []
        for instruction in final_ir:
            instr_type = instruction.get("type")
            line_num = instruction.get("line", -1)  # Get the line number

            if instr_type == "copy" and isinstance(instruction.get("source"), list):
                dests = instruction.get("result", [])
                srcs = instruction.get("source", [])
                for dest_var, src_var in zip(dests, srcs):
                    single_copy_instr = {"type": "copy", "result": [dest_var], "source": src_var}
                    op_code_val = self._resolve_opcode(single_copy_instr)
                    dest_op = [self._resolve_operand(dest_var)]
                    src_op = [self._resolve_operand(src_var)]
                    bytecode.append({"op": op_code_val, "dests": dest_op, "srcs": src_op, "line": line_num})
                continue

            op_code_val = 0
            dests: List[int] = []
            srcs: List[int] = []

            if instr_type in ("execution_assignment", "copy", "literal_assignment"):
                if instr_type == "literal_assignment":
                    instruction = {"function": "copy", "result": instruction["result"], "args": [instruction["value"]]}
                op_code_val = self._resolve_opcode(instruction)
                dests = [self._resolve_operand(res) for res in instruction.get("result", [])]
                srcs_values = instruction.get("args", []) if instr_type != "copy" else [instruction.get("source")]
                srcs = [self._resolve_operand(val) for val in srcs_values]
            elif instr_type == "jump":
                op_code_val = OpCode.JUMP.value
                srcs = [label_map[instruction["target"]]]
            elif instr_type == "jump_if_false":
                op_code_val = OpCode.JUMP_IF_FALSE.value
                condition_op = self._resolve_operand(instruction["condition"])
                target_addr = label_map[instruction["target"]]
                srcs = [condition_op, target_addr]

            bytecode.append({"op": op_code_val, "dests": dests, "srcs": srcs, "line": line_num})

        return bytecode

    def _pack_operand(self, op_type: OperandType, index: int) -> int:
        return (op_type.value << 27) | index

    def _get_canonical_key(self, literal: Any) -> str:
        if isinstance(literal, (int, float)):
            return f"s_{float(literal)}"
        if isinstance(literal, bool):
            return f"b_{str(literal).lower()}"
        if isinstance(literal, (_StringLiteral, str)):
            val = literal.value if isinstance(literal, _StringLiteral) else literal
            return f"str_{val}"
        if isinstance(literal, list):
            return f"v_{'_'.join([self._get_canonical_key(item) for item in literal])}"
        return ""

    def _resolve_operand(self, value: Any) -> int:
        if isinstance(value, str):
            var_info = self.variable_map[value]
            op_type = OperandType[f"{var_info['type']}_REG"]
            return self._pack_operand(op_type, var_info["index"])
        else:
            key = self._get_canonical_key(value)
            const_info = self.constant_map[key]
            op_type = OperandType[f"{const_info['type']}_CONST"]
            return self._pack_operand(op_type, const_info["index"])

    def _get_type_of_value(self, value: Any) -> str:
        if isinstance(value, str):
            return self.variable_map[value]["type"]
        else:
            key = self._get_canonical_key(value)
            return self.constant_map[key]["type"]

    def _resolve_opcode(self, instruction: Dict[str, Any]) -> int:
        func_name = instruction.get("function")
        if instruction.get("type") == "copy" or func_name == "copy":
            func_name = "copy"
            src_values = instruction.get("args", [instruction.get("source")])
        else:
            src_values = instruction.get("args", [])

        if func_name.startswith("__") and func_name.endswith("__"):
            func_name = func_name.strip("_")

        dest_types = [self.variable_map[res]["type"] for res in instruction.get("result", [])]
        src_types = [self._get_type_of_value(val) for val in src_values]

        dest_key = "".join(self.type_char_map[t] for t in dest_types)
        src_key = "".join(self.type_char_map[t] for t in src_types)

        isa_key = f"{func_name}_{dest_key}_{src_key}"
        return OpCode[isa_key].value
