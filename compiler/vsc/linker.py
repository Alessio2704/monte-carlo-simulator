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
    1. Builds the variable registry.
    2. Resolves all variable names to integer indices.
    3. Generates the final low-level JSON bytecode.
    """
    all_steps = pre_trial_steps + per_trial_steps
    all_variable_names = {step["result"] for step in all_steps}

    # 1. Create the canonical, ordered registry. Sorting ensures deterministic output.
    variable_registry_list = sorted(list(all_variable_names))
    name_to_index_map = {name: i for i, name in enumerate(variable_registry_list)}

    # 2. Resolve the output variable string name to its index.
    if output_var and output_var not in name_to_index_map:
        raise ValuaScriptError(f"The final @output variable '{output_var}' was not found in the final execution plan. It may have been eliminated as dead code.")
    output_variable_index = name_to_index_map.get(output_var)

    # 3. Define recursive helper to rewrite expressions into bytecode format
    def _resolve_expression_to_bytecode(arg):
        if isinstance(arg, Token):  # This is a variable name
            var_name = str(arg)
            return {"type": "variable_index", "value": name_to_index_map[var_name]}
        if isinstance(arg, dict) and "args" in arg:  # This is a nested function call
            new_arg = arg.copy()
            new_arg["args"] = [_resolve_expression_to_bytecode(a) for a in new_arg["args"]]
            return new_arg
        return arg  # It's a literal (number, _StringLiteral, etc.)

    # 4. Define helper to rewrite a list of steps
    def _rewrite_steps_to_bytecode(steps_to_rewrite):
        bytecode_steps = []
        for step in steps_to_rewrite:
            new_step = {
                "type": step["type"],
                "result_index": name_to_index_map[step["result"]],
                "line": step.get("line", -1),
            }
            if new_step["type"] == "literal_assignment":
                new_step["value"] = step["value"]
            else:  # execution_assignment
                new_step["function"] = step["function"]
                new_step["args"] = [_resolve_expression_to_bytecode(a) for a in step.get("args", [])]

            # Final cleanup for JSON serialization
            if "value" in new_step and isinstance(new_step.get("value"), (Token, _StringLiteral)):
                new_step["value"] = _process_arg_for_json(new_step["value"])
            if "args" in new_step:
                new_step["args"] = [_process_arg_for_json(a) for a in new_step["args"]]
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
