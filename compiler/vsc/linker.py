from lark import Token
from .parser import _StringLiteral
from .exceptions import ValuaScriptError


def _process_arg_for_json(arg):
    """A final pass to convert any custom classes into JSON-serializable formats."""
    if isinstance(arg, _StringLiteral):
        return {"type": "string_literal", "value": arg.value}
    if isinstance(arg, Token):
        raise TypeError(f"Internal Error: Unexpected unresolved Token '{arg}' during final JSON serialization.")
    if isinstance(arg, dict) and "args" in arg:
        arg["args"] = [_process_arg_for_json(a) for a in arg["args"]]
    return arg


def link_and_generate_bytecode(pre_trial_steps, per_trial_steps, sim_config, output_var):
    """
    Performs the final "linking" stage:
    1. Builds the variable registry.
    2. Resolves all variable names to integer indices.
    3. Generates the final low-level JSON bytecode.
    """
    all_steps = pre_trial_steps + per_trial_steps
    all_variable_names = set()
    for step in all_steps:
        results = step.get("results") or [step.get("result")]
        all_variable_names.update(results)

    variable_registry_list = sorted(list(all_variable_names))
    name_to_index_map = {name: i for i, name in enumerate(variable_registry_list)}

    output_variable_index = None
    if output_var:
        if output_var not in name_to_index_map:
            raise ValuaScriptError(f"The final @output variable '{output_var}' was not found. It may have been eliminated as dead code.")
        output_variable_index = name_to_index_map.get(output_var)

    def _resolve_expression_to_bytecode(arg):
        if isinstance(arg, Token):
            return {"type": "variable_index", "value": name_to_index_map[str(arg)]}
        if isinstance(arg, dict) and arg.get("type") == "conditional_expression":
            return {
                "type": "conditional_expression",
                "condition": _resolve_expression_to_bytecode(arg["condition"]),
                "then_expr": _resolve_expression_to_bytecode(arg["then_expr"]),
                "else_expr": _resolve_expression_to_bytecode(arg["else_expr"]),
            }
        if isinstance(arg, dict) and "function" in arg:
            new_arg = arg.copy()
            new_arg["type"] = "execution_assignment"
            new_arg["args"] = [_resolve_expression_to_bytecode(a) for a in new_arg["args"]]
            return new_arg
        if isinstance(arg, bool):
            return {"type": "boolean_literal", "value": arg}
        if isinstance(arg, (int, float)):
            return {"type": "scalar_literal", "value": arg}
        if isinstance(arg, list):
            return {"type": "vector_literal", "value": arg}
        if isinstance(arg, _StringLiteral):
            return {"type": "string_literal", "value": arg.value}
        raise TypeError(f"Internal Error: Unhandled type '{type(arg).__name__}' during bytecode generation.")

    def _rewrite_steps_to_bytecode(steps_to_rewrite):
        bytecode_steps = []
        for step in steps_to_rewrite:
            step_type = step["type"]
            if step_type == "literal_assignment":
                new_step = {"type": "literal_assignment", "result": name_to_index_map[step["result"]], "line": step.get("line", -1), "value": step["value"]}
            elif step_type == "conditional_expression":
                new_step = {
                    "type": "conditional_assignment",
                    "result": name_to_index_map[step["result"]],
                    "line": step.get("line", -1),
                    "condition": _resolve_expression_to_bytecode(step["condition"]),
                    "then_expr": _resolve_expression_to_bytecode(step["then_expr"]),
                    "else_expr": _resolve_expression_to_bytecode(step["else_expr"]),
                }
            else:
                results = step.get("results") or [step.get("result")]
                new_step = {
                    "type": "execution_assignment",
                    "result": [name_to_index_map[r] for r in results],
                    "line": step.get("line", -1),
                    "function": step["function"],
                    "args": [_resolve_expression_to_bytecode(a) for a in step.get("args", [])],
                }
            bytecode_steps.append(new_step)
        return bytecode_steps

    bytecode_pre_trial = _rewrite_steps_to_bytecode(pre_trial_steps)
    bytecode_per_trial = _rewrite_steps_to_bytecode(per_trial_steps)

    return {
        "simulation_config": sim_config,
        "variable_registry": variable_registry_list,
        "output_variable_index": output_variable_index,
        "pre_trial_steps": bytecode_pre_trial,
        "per_trial_steps": bytecode_per_trial,
    }
