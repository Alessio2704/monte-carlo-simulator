from lark import Token
from .parser import _StringLiteral
from .exceptions import ValuaScriptError


def _process_arg_for_json(arg):
    """A final pass to convert any custom classes into JSON-serializable formats."""
    if isinstance(arg, _StringLiteral):
        return {"type": "string_literal", "value": arg.value}
    if isinstance(arg, Token):
        # This should only happen for non-variable tokens if any exist.
        # Variable tokens should have been resolved to indices already.
        raise TypeError(f"Internal Error: Unexpected unresolved Token '{arg}' during final JSON serialization.")
    if isinstance(arg, dict) and "args" in arg:
        arg["args"] = [_process_arg_for_json(a) for a in arg["args"]]
    return arg


def link_and_generate_bytecode(pre_trial_steps, per_trial_steps, sim_config, output_var):
    """
    Performs the final "linking" stage:
    1. Builds the variable registry from all single and multi-assignments.
    2. Resolves all variable names to integer indices.
    3. Generates the final low-level JSON bytecode.
    """
    all_steps = pre_trial_steps + per_trial_steps
    all_variable_names = set()
    for step in all_steps:
        if "result" in step:
            all_variable_names.add(step["result"])
        elif "results" in step:
            all_variable_names.update(step["results"])

    # 1. Create the canonical, ordered registry. Sorting ensures deterministic output.
    variable_registry_list = sorted(list(all_variable_names))
    name_to_index_map = {name: i for i, name in enumerate(variable_registry_list)}

    # 2. Resolve the output variable string name to its index.
    output_variable_index = None
    if output_var:  # This will be None for a module file, skipping the block
        if output_var not in name_to_index_map:
            raise ValuaScriptError(f"The final @output variable '{output_var}' was not found in the final execution plan. It may have been eliminated as dead code.")
        output_variable_index = name_to_index_map.get(output_var)

    # 3. Define recursive helper to rewrite expressions into bytecode format
    def _resolve_expression_to_bytecode(arg):
        if isinstance(arg, Token):  # This is a variable name
            var_name = str(arg)
            return {"type": "variable_index", "value": name_to_index_map[var_name]}
        if isinstance(arg, dict) and arg.get("type") == "conditional_expression":
            return {
                "type": "conditional_expression",
                "condition": _resolve_expression_to_bytecode(arg["condition"]),
                "then_expr": _resolve_expression_to_bytecode(arg["then_expr"]),
                "else_expr": _resolve_expression_to_bytecode(arg["else_expr"]),
            }
        if isinstance(arg, dict) and "function" in arg:  # This is a nested function call
            new_arg = arg.copy()
            new_arg["type"] = "execution_assignment"
            new_arg["args"] = [_resolve_expression_to_bytecode(a) for a in new_arg["args"]]
            return new_arg

        # It's a literal value, wrap it in a typed dictionary
        if isinstance(arg, bool):
            return {"type": "boolean_literal", "value": arg}
        if isinstance(arg, (int, float)):
            return {"type": "scalar_literal", "value": arg}
        if isinstance(arg, list):
            return {"type": "vector_literal", "value": arg}
        if isinstance(arg, _StringLiteral):
            return {"type": "string_literal", "value": arg.value}

        raise TypeError(f"Internal Error: Unhandled type '{type(arg).__name__}' during bytecode generation.")

    # 4. Define helper to rewrite a list of steps
    def _rewrite_steps_to_bytecode(steps_to_rewrite):
        bytecode_steps = []
        for step in steps_to_rewrite:
            step_type = step["type"]
            if step_type == "multi_assignment":
                expression = step.get("expression", step)

                if expression.get("type") == "conditional_expression":
                    new_step = {
                        "type": "multi_conditional_assignment",
                        "result_indices": [name_to_index_map[r] for r in step["results"]],
                        "line": step.get("line", -1),
                        "condition": _resolve_expression_to_bytecode(expression["condition"]),
                        "then_expr": _resolve_expression_to_bytecode(expression["then_expr"]),
                        "else_expr": _resolve_expression_to_bytecode(expression["else_expr"]),
                    }
                else:  # It's a standard multi-assignment from a function call
                    new_step = {
                        "type": "multi_execution_assignment",
                        "result_indices": [name_to_index_map[r] for r in step["results"]],
                        "line": step.get("line", -1),
                        "function": expression["function"],
                        "args": [_resolve_expression_to_bytecode(a) for a in expression.get("args", [])],
                    }
            else:  # Handle single assignment
                new_step = {
                    "type": step_type,
                    "result_index": name_to_index_map[step["result"]],
                    "line": step.get("line", -1),
                }
                if new_step["type"] == "literal_assignment":
                    new_step["value"] = step["value"]
                elif new_step["type"] == "conditional_expression":
                    new_step["type"] = "conditional_assignment"  # Rename for the engine
                    new_step["condition"] = _resolve_expression_to_bytecode(step["condition"])
                    new_step["then_expr"] = _resolve_expression_to_bytecode(step["then_expr"])
                    new_step["else_expr"] = _resolve_expression_to_bytecode(step["else_expr"])
                else:  # execution_assignment
                    new_step["function"] = step["function"]
                    new_step["args"] = [_resolve_expression_to_bytecode(a) for a in step.get("args", [])]

            bytecode_steps.append(new_step)
        return bytecode_steps

    # 5. Generate the final bytecode
    bytecode_pre_trial = _rewrite_steps_to_bytecode(pre_trial_steps)
    bytecode_per_trial = _rewrite_steps_to_bytecode(per_trial_steps)

    # 6. Assemble the final recipe object
    return {
        "simulation_config": sim_config,
        "variable_registry": variable_registry_list,
        "output_variable_index": output_variable_index,
        "pre_trial_steps": bytecode_pre_trial,
        "per_trial_steps": bytecode_per_trial,
    }
