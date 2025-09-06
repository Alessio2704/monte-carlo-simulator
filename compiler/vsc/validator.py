from lark import Token
from collections import deque

from .exceptions import ValuaScriptError
from .parser import _StringLiteral
from .config import FUNCTION_SIGNATURES, DIRECTIVE_CONFIG


def _check_for_recursive_calls(user_functions):
    """Builds a call graph and detects cycles to prevent infinite recursion during inlining."""
    call_graph = {name: set() for name in user_functions}

    for func_name, func_def in user_functions.items():
        queue = deque(func_def["body"])
        while queue:
            item = queue.popleft()
            if isinstance(item, dict):
                if "function" in item and item["function"] in user_functions:
                    call_graph[func_name].add(item["function"])
                for value in item.values():
                    if isinstance(value, list):
                        queue.extend(value)
                    elif isinstance(value, dict):
                        queue.append(value)

    visiting = set()
    visited = set()

    def has_cycle(node, path):
        visiting.add(node)
        path.append(node)
        for neighbor in sorted(list(call_graph.get(node, []))):
            if neighbor in visiting:
                path.append(neighbor)
                return True, path
            if neighbor not in visited:
                is_cyclic, final_path = has_cycle(neighbor, path)
                if is_cyclic:
                    return True, final_path
        visiting.remove(node)
        visited.add(node)
        path.pop()
        return False, []

    for func_name in sorted(list(user_functions.keys())):
        if func_name not in visited:
            is_cyclic, path = has_cycle(func_name, [])
            if is_cyclic:
                cycle_path_str = " -> ".join(path)
                raise ValuaScriptError(f"Recursive function call detected: {cycle_path_str}")


def _infer_expression_type(expression_dict, defined_vars, line_num, current_result_var, all_signatures={}):
    """Recursively infers the type of a variable based on the expression it is assigned to."""
    expr_type = expression_dict.get("type")
    if expr_type == "literal_assignment":
        value = expression_dict.get("value")
        if isinstance(value, (int, float)):
            return "scalar"
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, (int, float)):
                    error_val = f'"{item.value}"' if isinstance(item, _StringLiteral) else str(item)
                    raise ValuaScriptError(f"L{line_num}: Invalid item {error_val} in vector literal for '{current_result_var}'.")
            return "vector"
        if isinstance(value, _StringLiteral):
            return "string"
        raise ValuaScriptError(f"L{line_num}: Invalid value for '{current_result_var}'.")

    if expr_type == "execution_assignment":
        func_name = expression_dict["function"]
        args = expression_dict.get("args", [])
        signature = all_signatures.get(func_name)
        if not signature:
            raise ValuaScriptError(f"L{line_num}: Unknown function '{func_name}'.")

        if not signature.get("variadic", False) and len(args) != len(signature["arg_types"]):
            raise ValuaScriptError(f"L{line_num}: Function '{func_name}' expects {len(signature['arg_types'])} argument(s), but got {len(args)}.")

        inferred_arg_types = []
        for arg in args:
            arg_type = None
            if isinstance(arg, Token):
                var_name = str(arg)
                if var_name not in defined_vars:
                    raise ValuaScriptError(f"L{line_num}: Variable '{var_name}' used in function '{func_name}' is not defined.")
                arg_type = defined_vars[var_name]["type"]
            elif isinstance(arg, _StringLiteral):
                arg_type = "string"
            else:
                temp_dict = {"type": "execution_assignment", **arg} if isinstance(arg, dict) else {"type": "literal_assignment", "value": arg}
                arg_type = _infer_expression_type(temp_dict, defined_vars, line_num, current_result_var, all_signatures)
            inferred_arg_types.append(arg_type)

        if not signature.get("variadic"):
            for i, expected_type in enumerate(signature["arg_types"]):
                if expected_type != "any" and expected_type != inferred_arg_types[i]:
                    raise ValuaScriptError(f"L{line_num}: Argument {i+1} for '{func_name}' expects a '{expected_type}', but got a '{inferred_arg_types[i]}'.")

        return_type_rule = signature["return_type"]
        return return_type_rule(inferred_arg_types) if callable(return_type_rule) else return_type_rule

    raise ValuaScriptError(f"L{line_num}: Could not determine type for '{current_result_var}'.")


def validate_and_inline_udfs(execution_steps, user_functions, all_signatures):
    """Validates user-defined functions and then performs inlining."""
    # 1. Validate UDF bodies
    for func_name, func_def in user_functions.items():
        local_vars = {p["name"]: {"type": p["type"], "line": func_def["line"]} for p in func_def["params"]}
        has_return = False
        for step in func_def["body"]:
            if step.get("type") == "return_statement":
                has_return = True
                return_identity_expr = {"type": "execution_assignment", "function": "identity", "args": [step["value"]]}
                return_type = _infer_expression_type(return_identity_expr, local_vars, func_def["line"], "return", all_signatures)
                if return_type != func_def["return_type"]:
                    raise ValuaScriptError(f"L{func_def['line']}: Function '{func_name}' returns type '{return_type}' but is defined to return '{func_def['return_type']}'.")
            else:
                line, result_var = step["line"], step["result"]
                if result_var in local_vars:
                    raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once in function '{func_name}'.")
                rhs_type = _infer_expression_type(step, local_vars, line, result_var, all_signatures)
                local_vars[result_var] = {"type": rhs_type, "line": line}
        if not has_return:
            raise ValuaScriptError(f"L{func_def['line']}: Function '{func_name}' is missing a return statement.")

    # 2. Perform Inlining
    inlined_code = list(execution_steps)
    call_count = 0
    temp_var_count = 0

    while True:
        contains_udf_call = any(s.get("type") == "execution_assignment" and s.get("function") in user_functions for s in inlined_code)
        contains_nested_udf_call = any(isinstance(arg, dict) and arg.get("function") in user_functions for s in inlined_code if s.get("type") == "execution_assignment" for arg in s.get("args", []))

        if not contains_udf_call and not contains_nested_udf_call:
            break

        # --- FLATTENING PASS: Hoist nested UDF calls ---
        flattened_steps = []
        for step in inlined_code:
            if step.get("type") != "execution_assignment" or not any(isinstance(arg, dict) and arg.get("function") in user_functions for arg in step.get("args", [])):
                flattened_steps.append(step)
                continue

            modified_args = []
            for arg in step.get("args", []):
                if isinstance(arg, dict) and arg.get("function") in user_functions:
                    temp_var_count += 1
                    temp_var_name = f"__temp_{temp_var_count}"
                    nested_call_step = {"result": temp_var_name, "line": step["line"], "type": "execution_assignment", **arg}
                    flattened_steps.append(nested_call_step)
                    modified_args.append(Token("CNAME", temp_var_name))
                else:
                    modified_args.append(arg)
            modified_step = step.copy()
            modified_step["args"] = modified_args
            flattened_steps.append(modified_step)
        inlined_code = flattened_steps

        # --- INLINING PASS: Expand top-level UDF calls ---
        next_pass_steps = []
        for step in inlined_code:
            if step.get("type") == "execution_assignment" and step.get("function") in user_functions:
                func_name = step["function"]
                func_def = user_functions[func_name]

                # ** THE FIX IS HERE **
                # Perform arity check BEFORE attempting to inline the function call.
                expected_argc = len(func_def["params"])
                provided_argc = len(step["args"])
                if provided_argc != expected_argc:
                    raise ValuaScriptError(f"L{step['line']}: Function '{func_name}' expects {expected_argc} argument(s), but got {provided_argc}.")

                call_count += 1
                mangling_prefix = f"__{func_name}_{call_count}__"
                param_names = {p["name"] for p in func_def["params"]}
                local_var_names = {s["result"] for s in func_def["body"] if "result" in s}
                arg_map = {}
                for i, param in enumerate(func_def["params"]):
                    mangled_param_name = f"{mangling_prefix}{param['name']}"
                    next_pass_steps.append({"result": mangled_param_name, "type": "execution_assignment", "function": "identity", "args": [step["args"][i]], "line": step["line"]})
                    arg_map[param["name"]] = Token("CNAME", mangled_param_name)

                def mangle_expression(expr):
                    if isinstance(expr, Token):
                        var_name = str(expr)
                        if var_name in param_names:
                            return arg_map[var_name]
                        if var_name in local_var_names:
                            return Token("CNAME", f"{mangling_prefix}{var_name}")
                    elif isinstance(expr, dict) and "args" in expr:
                        new_expr = expr.copy()
                        new_expr["args"] = [mangle_expression(a) for a in expr["args"]]
                        return new_expr
                    return expr

                for body_step in func_def["body"]:
                    if body_step.get("type") == "return_statement":
                        mangled_return_value = mangle_expression(body_step["value"])
                        final_assignment = {"result": step["result"], "line": step["line"]}
                        if isinstance(mangled_return_value, dict):
                            final_assignment.update({"type": "execution_assignment", **mangled_return_value})
                        elif isinstance(mangled_return_value, Token):
                            final_assignment.update({"type": "execution_assignment", "function": "identity", "args": [mangled_return_value]})
                        else:
                            final_assignment.update({"type": "literal_assignment", "value": mangled_return_value})
                        next_pass_steps.append(final_assignment)
                    else:
                        mangled_step = body_step.copy()
                        mangled_step["result"] = f"{mangling_prefix}{mangled_step['result']}"
                        if mangled_step.get("type") == "execution_assignment":
                            mangled_step["args"] = [mangle_expression(arg) for arg in mangled_step.get("args", [])]
                        elif mangled_step.get("type") == "literal_assignment" and isinstance(mangled_step.get("value"), list):
                            mangled_step["value"] = [mangle_expression(item) for item in mangled_step["value"]]
                        next_pass_steps.append(mangled_step)
            else:
                next_pass_steps.append(step)
        inlined_code = next_pass_steps
    return inlined_code


def validate_semantics(high_level_ast, is_preview_mode):
    """Performs all semantic validation and returns the final, inlined execution steps."""
    user_functions = {f["name"]: f for f in high_level_ast.get("function_definitions", [])}
    execution_steps = high_level_ast.get("execution_steps", [])

    _check_for_recursive_calls(user_functions)

    udf_signatures = {}
    for func_name, func_def in user_functions.items():
        if func_name in FUNCTION_SIGNATURES:
            raise ValuaScriptError(f"L{func_def['line']}: Cannot redefine built-in function '{func_name}'.")
        udf_signatures[func_name] = {"variadic": False, "arg_types": [p["type"] for p in func_def["params"]], "return_type": func_def["return_type"]}
    all_signatures = {**FUNCTION_SIGNATURES, **udf_signatures}

    inlined_steps = validate_and_inline_udfs(execution_steps, user_functions, all_signatures)

    # Validate main body semantics
    defined_vars = {}
    for step in inlined_steps:
        line, result_var = step["line"], step["result"]
        if result_var in defined_vars:
            raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once.")
        rhs_type = _infer_expression_type(step, defined_vars, line, result_var, all_signatures)
        defined_vars[result_var] = {"type": rhs_type, "line": line}

    # Validate directives
    raw_directives_list = high_level_ast.get("directives", [])
    seen_directives, directives = set(), {}
    for d in raw_directives_list:
        name = d["name"]
        if name not in DIRECTIVE_CONFIG:
            raise ValuaScriptError(f"L{d['line']}: Unknown directive '@{name}'.")
        if name in seen_directives and not is_preview_mode:
            raise ValuaScriptError(f"L{d['line']}: The directive '@{name}' is defined more than once.")
        seen_directives.add(name)
        directives[name] = d

    sim_config, output_var = {}, ""
    for name, config in DIRECTIVE_CONFIG.items():
        if not is_preview_mode and config["required"] and name not in directives:
            raise ValuaScriptError(config["error_missing"])
        if name in directives:
            d = directives[name]
            raw_value = d["value"]
            # Perform type checking on directive values
            if config["type"] is str and name == "output_file" and not isinstance(raw_value, _StringLiteral):
                raise ValuaScriptError(f"L{d['line']}: {config['error_type']}")
            elif config["type"] is str and name == "output" and not isinstance(raw_value, Token):
                raise ValuaScriptError(f"L{d['line']}: {config['error_type']}")

            value_for_validation = raw_value.value if isinstance(raw_value, _StringLiteral) else (str(raw_value) if isinstance(raw_value, Token) else raw_value)
            if config["type"] is int and not isinstance(value_for_validation, int):
                raise ValuaScriptError(f"L{d['line']}: {config['error_type']}")

            # Store validated directive values
            if name == "iterations":
                sim_config["num_trials"] = value_for_validation
            elif name == "output":
                output_var = value_for_validation
            elif name == "output_file":
                sim_config["output_file"] = value_for_validation

    if not is_preview_mode and not output_var:
        raise ValuaScriptError(DIRECTIVE_CONFIG["output"]["error_missing"])

    if not is_preview_mode and output_var not in defined_vars:
        raise ValuaScriptError(f"The final @output variable '{output_var}' is not defined.")

    return inlined_steps, defined_vars, sim_config, output_var
