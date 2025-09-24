from typing import Dict, Any, List, Union, Tuple
import re

from ..parser import _StringLiteral
from ..exceptions import InternalCompilerError


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
        signature = self.signatures[func_name]
        return_type_rule = signature["return_type"]

        for i in range(1, len(args)):
            is_last_arg = i == len(args) - 1

            if is_last_arg:
                result_var = instruction["result"]
            else:
                left_type, left_stochastic = self._get_expression_details(current_result)
                right_type, right_stochastic = self._get_expression_details(args[i])

                if callable(return_type_rule):
                    result_type_str = return_type_rule([left_type[0], right_type[0]])
                else:
                    result_type_str = return_type_rule

                result_is_stochastic = left_stochastic or right_stochastic
                [temp_var_name] = self._create_and_add_temp_vars_to_model([result_type_str], is_stochastic=result_is_stochastic)
                result_var = [temp_var_name]

            binary_op = {"type": "execution_assignment", "result": result_var, "function": func_name, "args": [current_result, args[i]], "line": line}
            decomposed.append(binary_op)
            current_result = result_var[0]

        return decomposed

    def _process_and_lift_instruction(self, instruction: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
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
        if isinstance(expr, (int, float)):
            return ["scalar"], False
        if isinstance(expr, bool):
            return ["boolean"], False
        if isinstance(expr, _StringLiteral):
            return ["string"], False
        if isinstance(expr, list):
            return ["vector"], any(self._get_expression_details(item)[1] for item in expr)

        if isinstance(expr, str):
            # First, check global and temporary variables.
            global_var_info = self.model.get("global_variables", {}).get(expr)
            if global_var_info:
                return [global_var_info["inferred_type"]], global_var_info.get("is_stochastic", False)

            # Second, check for mangled UDF local variables.
            mangled_match = re.match(r"^__(.+)_[0-9]+__(.+)$", expr)
            if mangled_match:
                original_func_name, original_var_name = mangled_match.groups()
                udf_info = self.model["user_defined_functions"].get(original_func_name)
                if udf_info:
                    # Check both discovered local variables and parameters for the type info
                    local_var_info = udf_info["discovered_body"].get(original_var_name)
                    if not local_var_info:
                        param_info = next((p for p in udf_info.get("params", []) if p["name"] == original_var_name), None)
                        if param_info:
                            return [param_info["type"]], False  # Params are not stochastic at definition
                    if local_var_info:
                        return [local_var_info["inferred_type"]], local_var_info.get("is_stochastic", False)

            raise InternalCompilerError(f"IRLowerer could not find type info for variable '{expr}'. This is a bug.")

        if isinstance(expr, dict):
            if expr.get("type") == "conditional_expression":
                then_type, then_stochastic = self._get_expression_details(expr["then_expr"])
                _, else_stochastic = self._get_expression_details(expr["else_expr"])
                _, cond_stochastic = self._get_expression_details(expr["condition"])
                return then_type, (then_stochastic or else_stochastic or cond_stochastic)

            if "function" in expr:
                sig = self.signatures.get(expr["function"], {})
                is_stochastic = sig.get("is_stochastic", False)

                arg_details = [self._get_expression_details(arg) for arg in expr.get("args", [])]
                if any(detail[1] for detail in arg_details):
                    is_stochastic = True

                return_type_rule = sig.get("return_type")
                if callable(return_type_rule):
                    arg_types = [details[0][0] for details in arg_details]
                    return_type = return_type_rule(arg_types)
                else:
                    return_type = return_type_rule

                final_return_type = [return_type] if isinstance(return_type, str) else return_type
                return final_return_type, is_stochastic

        raise InternalCompilerError(f"IRLowerer could not determine expression details for node: {expr}")

    def _create_and_add_temp_vars_to_model(self, var_types: List[str], is_stochastic: bool) -> List[str]:
        temp_names = []
        for var_type_str in var_types:
            self.temp_var_counter += 1
            temp_name = f"__temp_lifted_{self.temp_var_counter}"
            # Ensure we never create a variable with a null or 'any' type
            if not var_type_str or var_type_str == "any":
                raise InternalCompilerError(f"IRLowerer attempted to create a temporary variable with an unresolved type '{var_type_str}'.")
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
                if isinstance(source, list):
                    for i, result_var in enumerate(instruction["result"]):
                        lowered_ir.append({"type": "copy", "result": [result_var], "source": source[i], "line": instruction.get("line")})
                else:
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
