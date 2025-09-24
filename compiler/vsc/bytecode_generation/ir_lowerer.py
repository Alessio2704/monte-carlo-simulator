from typing import Dict, Any, List, Union, Tuple
import re


class IRLowerer:
    """
    Implements Phase 8a of the bytecode pipeline.

    This class is responsible for lowering the abstraction level of the IR.
    It takes the high-level, partitioned IR from the optimizer and converts
    it into a flat, linear sequence of simple, machine-like instructions.

    This is a stateful process that performs three main sub-phases:
    1.  Expression Flattening (Lifting): Eliminates all nested function calls
        and conditional expressions by introducing temporary variables.
    2.  Variadic Decomposition: Breaks down multi-argument instructions (like
        add(a,b,c)) into a sequential chain of binary operations.
    3.  Control-Flow Lowering: Replaces high-level conditional_assignment
        and multi-copy instructions with procedural sequences.
    """

    def __init__(self, partitioned_ir: Dict[str, List[Dict[str, Any]]], model: Dict[str, Any]):
        self.partitioned_ir = partitioned_ir
        self.model = model
        self.temp_var_counter = 0
        self.label_counter = 0
        self.signatures = model.get("all_signatures", {})
        self.variadic_functions = {"add", "multiply", "__and__", "__or__"}

    def lower(self) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
        """
        Runs the full lowering pipeline on both the pre-trial and per-trial
        partitions of the IR.
        """
        lowered_pre_trial = self._lower_ir_list(self.partitioned_ir.get("pre_trial_steps", []))
        lowered_per_trial = self._lower_ir_list(self.partitioned_ir.get("per_trial_steps", []))

        lowered_ir = {"pre_trial_steps": lowered_pre_trial, "per_trial_steps": lowered_per_trial}

        return lowered_ir, self.model

    def _lower_ir_list(self, ir_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Orchestrates the lowering sub-phases for a single list of instructions."""
        flattened_ir = self._flatten_ir_list(ir_list)
        control_flow_lowered_ir = self._lower_control_flow(flattened_ir)
        return control_flow_lowered_ir

    def _flatten_ir_list(self, ir_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Iterates through an IR list, lifting nested expressions and decomposing
        variadic function calls.
        """
        final_ir = []
        for instruction in ir_list:
            lifted_instructions, new_instruction = self._process_and_lift_instruction(instruction)
            final_ir.extend(lifted_instructions)

            # Decompose the (now flattened) instruction if it's variadic
            decomposed_instructions = self._decompose_variadic_instruction(new_instruction)
            final_ir.extend(decomposed_instructions)

        return final_ir

    def _decompose_variadic_instruction(self, instruction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        If an instruction is a variadic call with > 2 args, breaks it into
        a chain of binary calls. Otherwise, returns it as is.
        """
        func_name = instruction.get("function")
        args = instruction.get("args", [])

        if func_name not in self.variadic_functions or len(args) <= 2:
            return [instruction]

        decomposed = []
        line = instruction.get("line")
        current_result = args[0]

        # Chain the operations: result = (((a + b) + c) + d) ...
        for i in range(1, len(args)):
            is_last_arg = i == len(args) - 1

            if is_last_arg:
                # The final operation assigns to the original result variable
                result_var = instruction["result"]
            else:
                # Intermediate operations assign to a new temporary variable
                # We can safely assume scalar type for these math/logic operations
                [temp_var_name] = self._create_and_add_temp_vars_to_model(["scalar"], is_stochastic=False)  # Stochasticity is resolved later
                result_var = [temp_var_name]

            binary_op = {"type": "execution_assignment", "result": result_var, "function": func_name, "args": [current_result, args[i]], "line": line}
            decomposed.append(binary_op)
            current_result = result_var[0]

        return decomposed

    def _process_and_lift_instruction(self, instruction: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Lifts expressions from a single instruction and returns the new preceding instructions and the rewritten one."""
        lifted_instructions = []
        new_instruction = instruction.copy()

        line = new_instruction.get("line")
        for key in ["args", "condition", "then_expr", "else_expr", "value"]:
            if key in new_instruction:
                new_instruction[key] = self._lift_expressions_recursive(new_instruction[key], lifted_instructions, line)
        return lifted_instructions, new_instruction

    def _lift_expressions_recursive(self, node: Any, lifted_instructions: List[Dict[str, Any]], line: int) -> Any:
        if isinstance(node, list):
            return [self._lift_expressions_recursive(item, lifted_instructions, line) for item in node]
        if not isinstance(node, dict):
            return node
        for key in ["args", "condition", "then_expr", "else_expr"]:
            if key in node:
                node[key] = self._lift_expressions_recursive(node[key], lifted_instructions, line)
        is_function = "function" in node
        is_conditional = node.get("type") == "conditional_expression"
        if not (is_function or is_conditional):
            return node
        return_types, is_stochastic = self._get_expression_details(node)
        temp_var_names = self._create_and_add_temp_vars_to_model(return_types, is_stochastic)
        if is_function:
            lifted_instructions.append({"type": "execution_assignment", "result": temp_var_names, "function": node["function"], "args": node.get("args", []), "line": line})
        elif is_conditional:
            lifted_instructions.append(
                {"type": "conditional_assignment", "result": temp_var_names, "condition": node["condition"], "then_expr": node["then_expr"], "else_expr": node["else_expr"], "line": line}
            )
        return temp_var_names[0] if len(temp_var_names) == 1 else temp_var_names

    def _get_expression_details(self, expr: Any) -> Tuple[List[str], bool]:
        types = ["scalar"]
        if isinstance(expr, (int, float)):
            types = ["scalar"]
        elif isinstance(expr, bool):
            types = ["boolean"]
        elif isinstance(expr, list):
            types = ["vector"]
        elif isinstance(expr, str):
            var_info = self.model.get("global_variables", {}).get(expr)
            if var_info:
                types = [var_info["inferred_type"]]
        elif isinstance(expr, dict):
            if expr.get("type") == "conditional_expression":
                types, _ = self._get_expression_details(expr["then_expr"])
            elif "function" in expr:
                sig = self.signatures.get(expr["function"])
                if sig:
                    ret_type = sig.get("return_type")
                    if isinstance(ret_type, str):
                        types = [ret_type]
                    elif isinstance(ret_type, list):
                        types = ret_type
        is_stochastic = False
        if isinstance(expr, str):
            var_info = self.model.get("global_variables", {}).get(expr)
            if var_info:
                is_stochastic = var_info.get("is_stochastic", False)
        elif isinstance(expr, dict):
            if "function" in expr:
                sig = self.signatures.get(expr["function"], {})
                if sig.get("is_stochastic"):
                    is_stochastic = True
            for arg in expr.get("args", []):
                if self._get_expression_details(arg)[1]:
                    is_stochastic = True
            for key in ["condition", "then_expr", "else_expr"]:
                if key in expr and self._get_expression_details(expr[key])[1]:
                    is_stochastic = True
        return types, is_stochastic

    def _create_and_add_temp_vars_to_model(self, var_types: List[str], is_stochastic: bool) -> List[str]:
        temp_names = []
        for var_type_str in var_types:
            self.temp_var_counter += 1
            temp_name = f"__temp_lifted_{self.temp_var_counter}"
            self.model["global_variables"][temp_name] = {"inferred_type": var_type_str.lower(), "is_stochastic": is_stochastic}
            temp_names.append(temp_name)
        return temp_names

    def _lower_control_flow(self, ir_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        lowered_ir = []
        for instruction in ir_list:
            if instruction.get("type") == "conditional_assignment":
                lowered_ir.extend(self._lower_one_conditional(instruction))
            elif instruction.get("function") == "identity":
                source = instruction["args"][0]
                # --- Decompose multi-assignment copy here ---
                if isinstance(source, list):
                    for i, result_var in enumerate(instruction["result"]):
                        lowered_ir.append({"type": "copy", "result": [result_var], "source": source[i], "line": instruction.get("line")})
                else:  # Single assignment copy
                    lowered_ir.append({"type": "copy", "result": instruction["result"], "source": source, "line": instruction.get("line")})
            else:
                lowered_ir.append(instruction)
        return lowered_ir

    def _get_next_label_pair(self) -> Tuple[str, str]:
        base_index = self.label_counter
        self.label_counter += 2
        return f"__else_label_{base_index}", f"__end_label_{base_index + 1}"

    def _create_assignment_from_expr(self, result: List[str], expr: Any, line: int) -> Dict:
        if isinstance(expr, dict) and "function" in expr:
            return {"type": "execution_assignment", "result": result, "function": expr["function"], "args": expr.get("args", []), "line": line}
        elif isinstance(expr, str):
            return {"type": "copy", "result": result, "source": expr, "line": line}
        else:
            return {"type": "literal_assignment", "result": result, "value": expr, "line": line}

    def _lower_one_conditional(self, instruction: Dict[str, Any]) -> List[Dict[str, Any]]:
        else_label, end_label = self._get_next_label_pair()
        line = instruction.get("line")
        cond_jump = {"type": "jump_if_false", "condition": instruction["condition"], "target": else_label, "line": line}
        then_assign = self._create_assignment_from_expr(instruction["result"], instruction["then_expr"], line)
        end_jump = {"type": "jump", "target": end_label, "line": line}
        else_label_instr = {"type": "label", "name": else_label, "line": line}
        else_assign = self._create_assignment_from_expr(instruction["result"], instruction["else_expr"], line)
        end_label_instr = {"type": "label", "name": end_label, "line": line}
        return [cond_jump, then_assign, end_jump, else_label_instr, else_assign, end_label_instr]
