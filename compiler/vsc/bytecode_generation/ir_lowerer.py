from typing import Dict, Any, List, Union, Tuple
import re


class IRLowerer:
    """
    Implements Phase 8b of the bytecode pipeline.

    This class is responsible for lowering the abstraction level of the IR.
    It takes the high-level, partitioned IR from the optimizer and converts
    it into a flat, linear sequence of simple, machine-like instructions.

    This is a stateful process that performs two main sub-phases:
    1.  Expression Flattening (Lifting): Eliminates all nested function calls
        and conditional expressions by introducing temporary variables. This
        sub-phase modifies the resource registries from Phase 8a in-place.
    2.  Control-Flow Lowering: Replaces high-level conditional_assignment
        instructions with a procedural sequence of labels and jumps.
    """

    def __init__(self, partitioned_ir: Dict[str, List[Dict[str, Any]]], registries: Dict[str, Any], model: Dict[str, Any]):
        self.partitioned_ir = partitioned_ir
        self.registries = registries
        self.model = model
        self.temp_var_counter = 0
        self.label_counter = 0

    def lower(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Runs the full lowering pipeline on both the pre-trial and per-trial
        partitions of the IR.
        """
        lowered_pre_trial = self._lower_ir_list(self.partitioned_ir.get("pre_trial_steps", []))
        lowered_per_trial = self._lower_ir_list(self.partitioned_ir.get("per_trial_steps", []))

        return {"pre_trial_steps": lowered_pre_trial, "per_trial_steps": lowered_per_trial}

    def _lower_ir_list(self, ir_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Orchestrates the two lowering sub-phases for a single list of instructions."""
        flattened_ir = self._flatten_ir_list(ir_list)
        control_flow_lowered_ir = self._lower_control_flow(flattened_ir)
        return control_flow_lowered_ir

    # --- Sub-phase B1: Expression Flattening (Lifting) ---

    def _flatten_ir_list(self, ir_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Iterates through an IR list, lifting all nested expressions into
        separate, preceding instructions.
        """
        final_ir = []
        for instruction in ir_list:
            lifted_instructions, new_instruction = self._process_and_lift_instruction(instruction)
            final_ir.extend(lifted_instructions)
            final_ir.append(new_instruction)
        return final_ir

    def _process_and_lift_instruction(self, instruction: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Lifts expressions from a single instruction and returns the new preceding instructions and the rewritten one."""
        lifted_instructions = []
        new_instruction = instruction.copy()

        # Recursively lift from all possible expression-holding fields
        if "args" in new_instruction:
            new_instruction["args"] = self._lift_expressions_recursive(new_instruction["args"], lifted_instructions, new_instruction.get("line"))
        if "condition" in new_instruction:
            new_instruction["condition"] = self._lift_expressions_recursive(new_instruction["condition"], lifted_instructions, new_instruction.get("line"))
        if "then_expr" in new_instruction:
            new_instruction["then_expr"] = self._lift_expressions_recursive(new_instruction["then_expr"], lifted_instructions, new_instruction.get("line"))
        if "else_expr" in new_instruction:
            new_instruction["else_expr"] = self._lift_expressions_recursive(new_instruction["else_expr"], lifted_instructions, new_instruction.get("line"))
        if "value" in new_instruction:
            new_instruction["value"] = self._lift_expressions_recursive(new_instruction["value"], lifted_instructions, new_instruction.get("line"))

        return lifted_instructions, new_instruction

    def _lift_expressions_recursive(self, node: Any, lifted_instructions: List[Dict[str, Any]], line: int) -> Any:
        """
        Recursively traverses an expression node. If it finds a nested function call
        or conditional expression, it 'lifts' it out into a new instruction and
        replaces it with a temporary variable.
        """
        if isinstance(node, list):
            return [self._lift_expressions_recursive(item, lifted_instructions, line) for item in node]

        if not isinstance(node, dict):
            return node

        # First, ensure the node's own children are flattened.
        if "args" in node:
            node["args"] = [self._lift_expressions_recursive(arg, lifted_instructions, line) for arg in node.get("args", [])]
        if "condition" in node:
            node["condition"] = self._lift_expressions_recursive(node["condition"], lifted_instructions, line)
        if "then_expr" in node:
            node["then_expr"] = self._lift_expressions_recursive(node["then_expr"], lifted_instructions, line)
        if "else_expr" in node:
            node["else_expr"] = self._lift_expressions_recursive(node["else_expr"], lifted_instructions, line)

        is_function = "function" in node
        is_conditional = node.get("type") == "conditional_expression"

        # If the node itself is not a liftable expression, return it as is.
        if not (is_function or is_conditional):
            return node

        # It IS a liftable expression. Create a temp var and lifted instruction.
        temp_var_name = self._create_and_register_temp_var(node)

        if is_function:
            lifted_instructions.append({"type": "execution_assignment", "result": [temp_var_name], "function": node["function"], "args": node.get("args", []), "line": line})
        elif is_conditional:
            lifted_instructions.append(
                {"type": "conditional_assignment", "result": [temp_var_name], "condition": node["condition"], "then_expr": node["then_expr"], "else_expr": node["else_expr"], "line": line}
            )

        return temp_var_name

    def _create_and_register_temp_var(self, expression_node: Dict[str, Any]) -> str:
        """Generates a new temporary variable, determines its type, and adds it to the registries."""
        self.temp_var_counter += 1
        temp_name = f"__temp_lifted_{self.temp_var_counter}"

        # Determine the type of the new variable. For now, we assume scalar.
        # A full implementation would look this up from the model's function signatures
        # or by inspecting the 'then_expr' of a conditional.
        # This simplification is acceptable for now as most expressions resolve to scalar.
        var_type_str = "scalar"
        registry_type = var_type_str.upper()

        # Update the registries from Phase 8a
        registry = self.registries["variable_registries"][registry_type]
        index = len(registry)
        registry.append(temp_name)
        self.registries["variable_map"][temp_name] = {"type": registry_type, "index": index}

        return temp_name

    # --- Sub-phase B2: High-Level Instruction Lowering ---

    def _lower_control_flow(self, ir_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans the flattened IR and replaces `conditional_assignment` with
        a sequence of labels and jumps.
        """
        lowered_ir = []
        for instruction in ir_list:
            if instruction.get("type") == "conditional_assignment":
                lowered_ir.extend(self._lower_one_conditional(instruction))
            elif instruction.get("function") == "identity":
                # Lower 'identity' calls to a more explicit 'copy' operation
                lowered_ir.append(
                    {
                        "type": "copy",
                        "result": instruction["result"],
                        "source": instruction["args"][0] if instruction.get("args") else None,
                        "line": instruction.get("line"),
                    }
                )
            else:
                lowered_ir.append(instruction)
        return lowered_ir

    def _get_next_label_pair(self) -> Tuple[str, str]:
        """Generates a pair of unique label names for an if/else structure."""
        base_index = self.label_counter
        self.label_counter += 2
        return f"__else_label_{base_index}", f"__end_label_{base_index + 1}"

    def _create_assignment_from_expr(self, result: List[str], expr: Any, line: int) -> Dict:
        """Helper to build a standard assignment from a result list and an expression node."""
        if isinstance(expr, dict) and "function" in expr:
            return {"type": "execution_assignment", "result": result, "function": expr["function"], "args": expr.get("args", []), "line": line}
        else:  # It's a literal value or a variable name
            return {"type": "literal_assignment", "result": result, "value": expr, "line": line}

    def _lower_one_conditional(self, instruction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates the full procedural sequence for a single conditional_assignment."""
        else_label, end_label = self._get_next_label_pair()
        line = instruction.get("line")

        # 1. The conditional jump to the 'else' block
        cond_jump = {"type": "jump_if_false", "condition": instruction["condition"], "target": else_label, "line": line}

        # 2. The "then" block assignment
        then_assign = self._create_assignment_from_expr(instruction["result"], instruction["then_expr"], line)

        # 3. The unconditional jump to skip the 'else' block
        end_jump = {"type": "jump", "target": end_label, "line": line}

        # 4. The 'else' label
        else_label_instr = {"type": "label", "name": else_label, "line": line}

        # 5. The "else" block assignment
        else_assign = self._create_assignment_from_expr(instruction["result"], instruction["else_expr"], line)

        # 6. The 'end' label
        end_label_instr = {"type": "label", "name": end_label, "line": line}

        return [cond_jump, then_assign, end_jump, else_label_instr, else_assign, end_label_instr]
