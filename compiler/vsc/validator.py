from lark import Token
from collections import deque
import os

from .exceptions import ValuaScriptError, ErrorCode
from .parser import _StringLiteral
from .config import FUNCTION_SIGNATURES, DIRECTIVE_CONFIG, OPERATOR_MAP


def _check_for_recursive_calls(user_functions):
    """Builds a call graph and detects cycles to prevent infinite recursion during inlining."""
    call_graph = {name: set() for name in user_functions}

    for func_name, func_def in user_functions.items():
        queue = deque(func_def["body"])
        while queue:
            item = queue.popleft()
            if isinstance(item, dict):
                # The function call is only a dependency if it's a User-Defined Function
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
                raise ValuaScriptError(ErrorCode.RECURSIVE_CALL_DETECTED, path=cycle_path_str)


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
                    raise ValuaScriptError(ErrorCode.INVALID_ITEM_IN_VECTOR, line=line_num, value=error_val, name=current_result_var)
            return "vector"
        if isinstance(value, _StringLiteral):
            return "string"
        raise ValuaScriptError(ErrorCode.INVALID_ITEM_IN_VECTOR, line=line_num, value=value, name=current_result_var)

    if expr_type == "execution_assignment":
        func_name = expression_dict["function"]
        args = expression_dict.get("args", [])
        signature = all_signatures.get(func_name)
        if not signature:
            raise ValuaScriptError(ErrorCode.UNKNOWN_FUNCTION, line=line_num, name=func_name)

        if not signature.get("variadic", False) and len(args) != len(signature["arg_types"]):
            raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line_num, name=func_name, expected=len(signature["arg_types"]), provided=len(args))

        inferred_arg_types = []
        for arg in args:
            arg_type = None
            if isinstance(arg, Token):
                var_name = str(arg)
                if var_name not in defined_vars:
                    raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE_IN_FUNC, line=line_num, name=var_name, func_name=func_name)
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
                    raise ValuaScriptError(ErrorCode.ARGUMENT_TYPE_MISMATCH, line=line_num, arg_num=i + 1, name=func_name, expected=expected_type, provided=inferred_arg_types[i])

        return_type_rule = signature["return_type"]
        return return_type_rule(inferred_arg_types) if callable(return_type_rule) else return_type_rule

    raise ValuaScriptError(ErrorCode.UNKNOWN_FUNCTION, line=line_num, name=current_result_var)


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
                    raise ValuaScriptError(ErrorCode.RETURN_TYPE_MISMATCH, line=func_def["line"], name=func_name, provided=return_type, expected=func_def["return_type"])
            else:
                line, result_var = step["line"], step["result"]
                if result_var in local_vars:
                    raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE_IN_FUNC, line=line, name=result_var, func_name=func_name)
                rhs_type = _infer_expression_type(step, local_vars, line, result_var, all_signatures)
                local_vars[result_var] = {"type": rhs_type, "line": line}
        if not has_return:
            raise ValuaScriptError(ErrorCode.MISSING_RETURN_STATEMENT, line=func_def["line"], name=func_name)

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

                expected_argc = len(func_def["params"])
                provided_argc = len(step["args"])
                if provided_argc != expected_argc:
                    raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=step["line"], name=func_name, expected=expected_argc, provided=provided_argc)

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


def validate_semantics(main_ast, all_user_functions, is_preview_mode, file_path=None):
    """Performs all semantic validation for a runnable script or a module file."""
    execution_steps = main_ast.get("execution_steps", [])

    directives = {}
    is_module = False
    for d in main_ast.get("directives", []):
        name = d["name"]
        if name == "module":
            is_module = True
        if name not in DIRECTIVE_CONFIG:
            raise ValuaScriptError(ErrorCode.UNKNOWN_DIRECTIVE, line=d["line"], name=name)
        if name in directives and not is_preview_mode:
            raise ValuaScriptError(ErrorCode.DUPLICATE_DIRECTIVE, line=d["line"], name=name)
        config = DIRECTIVE_CONFIG[name]
        if not config["value_allowed"] and d["value"] is not True:
            raise ValuaScriptError(ErrorCode.MODULE_WITH_VALUE, line=d["line"])
        directives[name] = d

    if is_module:
        if execution_steps:
            raise ValuaScriptError(ErrorCode.GLOBAL_LET_IN_MODULE, line=execution_steps[0]["line"])
        for name, d in directives.items():
            if not DIRECTIVE_CONFIG[name]["allowed_in_module"]:
                raise ValuaScriptError(ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, line=d["line"], name=name)

        RESERVED_NAMES = set(FUNCTION_SIGNATURES.keys()) | set(OPERATOR_MAP.values())
        for name, func_def in all_user_functions.items():
            if name in RESERVED_NAMES:
                raise ValuaScriptError(ErrorCode.REDEFINE_BUILTIN_FUNCTION, line=func_def["line"], name=name)

        _check_for_recursive_calls(all_user_functions)

        udf_signatures = {name: {"variadic": False, "arg_types": [p["type"] for p in fdef["params"]], "return_type": fdef["return_type"]} for name, fdef in all_user_functions.items()}
        all_signatures = {**FUNCTION_SIGNATURES, **udf_signatures}

        # Validate the bodies of this module's functions, using the full context.
        module_functions = {f["name"]: f for f in main_ast.get("function_definitions", [])}
        validate_and_inline_udfs([], module_functions, all_signatures)
        return [], {}, {}, None

    # --- Continue validation for a runnable script ---
    if not is_preview_mode:
        for name, config in DIRECTIVE_CONFIG.items():
            if name in ["import", "module"]:
                continue
            is_req = config["required"](directives) if callable(config["required"]) else config["required"]
            if is_req and name not in directives:
                code = ErrorCode.MISSING_ITERATIONS_DIRECTIVE if name == "iterations" else ErrorCode.MISSING_OUTPUT_DIRECTIVE
                raise ValuaScriptError(code)

    RESERVED_NAMES = set(FUNCTION_SIGNATURES.keys()) | set(OPERATOR_MAP.values())
    for name, func_def in all_user_functions.items():
        if name in RESERVED_NAMES:
            raise ValuaScriptError(ErrorCode.REDEFINE_BUILTIN_FUNCTION, line=func_def["line"], name=name)

    _check_for_recursive_calls(all_user_functions)

    udf_signatures = {name: {"variadic": False, "arg_types": [p["type"] for p in fdef["params"]], "return_type": fdef["return_type"]} for name, fdef in all_user_functions.items()}
    all_signatures = {**FUNCTION_SIGNATURES, **udf_signatures}

    validate_and_inline_udfs([], all_user_functions, all_signatures)

    defined_vars = {}
    for step in execution_steps:
        line, result_var = step["line"], step["result"]
        if result_var in defined_vars:
            raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE, line=line, name=result_var)
        rhs_type = _infer_expression_type(step, defined_vars, line, result_var, all_signatures)
        defined_vars[result_var] = {"type": rhs_type, "line": line}

    inlined_steps = validate_and_inline_udfs(execution_steps, all_user_functions, all_signatures)

    final_defined_vars = {}
    for step in inlined_steps:
        line, result_var = step["line"], step["result"]
        rhs_type = _infer_expression_type(step, final_defined_vars, line, result_var, all_signatures)
        final_defined_vars[result_var] = {"type": rhs_type, "line": line}

    sim_config, output_var = {}, ""
    for name, d in directives.items():
        config = DIRECTIVE_CONFIG.get(name)
        if config and config["value_allowed"]:
            raw_value = d["value"]
            value = raw_value.value if isinstance(raw_value, _StringLiteral) else (str(raw_value) if isinstance(raw_value, Token) else raw_value)

            if config.get("value_type") is int and not isinstance(value, int):
                raise ValuaScriptError(ErrorCode.INVALID_DIRECTIVE_VALUE, line=d["line"], error_msg=config["error_type"])
            if config.get("value_type") is str:
                if (name == "output_file" and not isinstance(raw_value, _StringLiteral)) or (name == "output" and not isinstance(raw_value, Token)):
                    raise ValuaScriptError(ErrorCode.INVALID_DIRECTIVE_VALUE, line=d["line"], error_msg=config["error_type"])

            if name == "iterations":
                sim_config["num_trials"] = value
            elif name == "output":
                output_var = value
            elif name == "output_file":
                # If the script being compiled has a path, resolve the output file
                # relative to that script's directory and make it absolute.
                if file_path:
                    base_dir = os.path.dirname(file_path)
                    sim_config["output_file"] = os.path.abspath(os.path.join(base_dir, value))
                else:
                    # For stdin, the path remains relative to the CWD.
                    sim_config["output_file"] = value

    if not is_preview_mode and output_var not in final_defined_vars:
        raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, name=output_var)

    return inlined_steps, final_defined_vars, sim_config, output_var
