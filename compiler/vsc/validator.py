from lark import Token
from collections import deque
import os

from .exceptions import ValuaScriptError, ErrorCode
from .parser import _StringLiteral
from .config import DIRECTIVE_CONFIG
from .functions import FUNCTION_SIGNATURES


def _format_udf_signature(func_def):
    """Formats a function definition dictionary into a readable signature string."""
    params_str = ", ".join([f"{p['name']}: {p['type']}" for p in func_def.get("params", [])])
    return_type = func_def["return_type"]
    if isinstance(return_type, list):
        return_str = f"({', '.join(return_type)})"
    else:
        return_str = return_type
    return f"func {func_def['name']}({params_str}) -> {return_str}"


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
                raise ValuaScriptError(ErrorCode.RECURSIVE_CALL_DETECTED, path=cycle_path_str)


def _infer_expression_type(expression_dict, defined_vars, line_num, current_result_var, all_signatures={}, func_name_context=None):
    """
    Recursively infers the type of a variable based on the expression it is assigned to.
    Can return a string for a single type or a list of strings for a multi-return type.
    """

    def _infer_sub_expression_type(sub_expr, func_name_context=None):
        if isinstance(sub_expr, Token):
            var_name = str(sub_expr)
            if var_name not in defined_vars:
                if func_name_context:
                    raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE_IN_FUNC, line=line_num, name=var_name, func_name=func_name_context)
                raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE_IN_FUNC, line=line_num, name=var_name, func_name="expression")
            return defined_vars[var_name]["type"]
        if isinstance(sub_expr, dict):
            return _infer_expression_type(sub_expr, defined_vars, line_num, "", all_signatures, func_name_context)
        temp_step = {"type": "literal_assignment", "value": sub_expr}
        return _infer_expression_type(temp_step, defined_vars, line_num, current_result_var, all_signatures)

    if expression_dict.get("_is_tuple_return"):
        raise ValuaScriptError(ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT, line=line_num, message="Cannot assign from a tuple literal. Multiple values can only be returned from a function.")

    expr_type = expression_dict.get("type", "execution_assignment")

    if expr_type == "literal_assignment":
        value = expression_dict.get("value")
        # Bool is evaluated first in order to not confuse it with an int later. It is mandatory it is here at the beginning
        if isinstance(value, bool):
            return "boolean"
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
        if isinstance(value, Token):
            identity_step = {"type": "execution_assignment", "function": "identity", "args": [value]}
            return _infer_expression_type(identity_step, defined_vars, line_num, current_result_var, all_signatures, func_name_context)
        raise TypeError(f"Internal Error: Unhandled literal value '{value}' of type '{type(value).__name__}'")

    if expr_type == "conditional_expression":
        condition_type = _infer_sub_expression_type(expression_dict["condition"], func_name_context)
        if condition_type != "boolean":
            raise ValuaScriptError(ErrorCode.IF_CONDITION_NOT_BOOLEAN, line=line_num, provided=condition_type)
        then_type = _infer_sub_expression_type(expression_dict["then_expr"], func_name_context)
        else_type = _infer_sub_expression_type(expression_dict["else_expr"], func_name_context)
        if then_type != else_type:
            # Format types for a clearer error message, especially for tuples
            then_type_str = f"({', '.join(then_type)})" if isinstance(then_type, list) else then_type
            else_type_str = f"({', '.join(else_type)})" if isinstance(else_type, list) else else_type
            raise ValuaScriptError(ErrorCode.IF_ELSE_TYPE_MISMATCH, line=line_num, then_type=then_type_str, else_type=else_type_str)
        return then_type

    if expr_type == "execution_assignment" or expr_type == "multi_assignment":
        if "expression" in expression_dict:
            sub_expr = expression_dict["expression"]
            # Case 1: let a, b = if selector then func1() else func2()
            if sub_expr.get("type") == "conditional_expression":
                # The type of the whole expression is the type of its branches, which must match.
                return _infer_expression_type(sub_expr, defined_vars, line_num, current_result_var, all_signatures, func_name_context)

            # Case 2: let a, b = some_function() -- promote the function call up.
            if isinstance(sub_expr, dict) and "function" in sub_expr:
                expression_dict.update(sub_expr)
                del expression_dict["expression"]
            else:
                raise ValuaScriptError(
                    ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT, line=line_num, message="The right side of a multi-assignment must be a function call or a conditional expression returning functions."
                )

        if "function" not in expression_dict:
            raise TypeError(f"Internal Error: Expression is not a function call: {expression_dict}")

        func_name = expression_dict["function"]
        args = expression_dict.get("args", [])
        signature = all_signatures.get(func_name)
        if not signature:
            raise ValuaScriptError(ErrorCode.UNKNOWN_FUNCTION, line=line_num, name=func_name)

        inferred_arg_types = [_infer_sub_expression_type(arg, func_name_context=func_name) for arg in args]

        if signature.get("variadic"):
            if signature["arg_types"]:
                expected_type = signature["arg_types"][0]
                for i, actual_type in enumerate(inferred_arg_types):
                    if expected_type != "any" and expected_type != actual_type:
                        op_name = func_name.strip("_")
                        if op_name in ("and", "or", "not"):
                            raise ValuaScriptError(ErrorCode.LOGICAL_OPERATOR_TYPE_MISMATCH, line=line_num, op=op_name, provided=actual_type)
                        raise ValuaScriptError(ErrorCode.ARGUMENT_TYPE_MISMATCH, line=line_num, arg_num=i + 1, name=func_name, expected=expected_type, provided=actual_type)
        else:
            if len(args) != len(signature["arg_types"]):
                raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line_num, name=func_name, expected=len(signature["arg_types"]), provided=len(args))
            if func_name in ("__eq__", "__neq__") and len(inferred_arg_types) == 2 and inferred_arg_types[0] != inferred_arg_types[1]:
                raise ValuaScriptError(ErrorCode.COMPARISON_TYPE_MISMATCH, line=line_num, op=func_name.strip("_"), left_type=inferred_arg_types[0], right_type=inferred_arg_types[1])
            for i, expected_type in enumerate(signature["arg_types"]):
                actual_type = inferred_arg_types[i]
                if expected_type != "any" and actual_type != expected_type:
                    op_name = func_name.strip("_")
                    if op_name in ("and", "or", "not"):
                        raise ValuaScriptError(ErrorCode.LOGICAL_OPERATOR_TYPE_MISMATCH, line=line_num, op=op_name, provided=actual_type)
                    raise ValuaScriptError(ErrorCode.ARGUMENT_TYPE_MISMATCH, line=line_num, arg_num=i + 1, name=func_name, expected=expected_type, provided=actual_type)

        return_type_rule = signature["return_type"]
        return return_type_rule(inferred_arg_types) if callable(return_type_rule) else return_type_rule

    if "function" in expression_dict:
        return _infer_expression_type({**expression_dict, "type": "execution_assignment"}, defined_vars, line_num, current_result_var, all_signatures, func_name_context)

    raise TypeError(f"Internal Error: Unhandled expression AST node: {expression_dict}")


def validate_and_inline_udfs(execution_steps, user_functions, all_signatures, initial_defined_vars):
    """Validates user-defined functions and then performs inlining."""
    for func_name, func_def in user_functions.items():
        local_vars = {p["name"]: {"type": p["type"], "line": func_def["line"]} for p in func_def["params"]}
        has_return = False
        for step in func_def["body"]:
            if step.get("type") == "return_statement":
                has_return = True
                expected_return_type = func_def["return_type"]

                if "values" in step:
                    returned_values = step["values"]
                    if not isinstance(expected_return_type, list) or len(returned_values) != len(expected_return_type):
                        raise ValuaScriptError(
                            ErrorCode.RETURN_TYPE_MISMATCH,
                            line=func_def["line"],
                            name=func_name,
                            provided=f"a tuple of {len(returned_values)} items",
                            expected=f"a tuple of {len(expected_return_type)} items",
                        )

                    for i, return_val in enumerate(returned_values):
                        temp_node = return_val
                        if isinstance(return_val, Token):
                            temp_node = {"type": "execution_assignment", "function": "identity", "args": [return_val]}
                        elif isinstance(return_val, dict) and "function" in temp_node and "type" not in temp_node:
                            temp_node["type"] = "execution_assignment"
                        elif not isinstance(return_val, dict):
                            temp_node = {"type": "literal_assignment", "value": return_val}

                        actual_type = _infer_expression_type(temp_node, local_vars, func_def["line"], f"return item {i+1}", all_signatures, func_name_context=func_name)
                        if actual_type != expected_return_type[i]:
                            raise ValuaScriptError(
                                ErrorCode.RETURN_TYPE_MISMATCH, line=func_def["line"], name=f"{func_name} (return item {i+1})", provided=actual_type, expected=expected_return_type[i]
                            )

                else:
                    if isinstance(expected_return_type, list):
                        raise ValuaScriptError(
                            ErrorCode.RETURN_TYPE_MISMATCH, line=func_def["line"], name=func_name, provided="a single value", expected=f"a tuple of {len(expected_return_type)} items"
                        )

                    return_val = step["value"]
                    temp_node = return_val
                    if isinstance(return_val, Token):
                        temp_node = {"type": "execution_assignment", "function": "identity", "args": [return_val]}
                    elif isinstance(return_val, dict) and "function" in temp_node and "type" not in temp_node:
                        temp_node["type"] = "execution_assignment"
                    elif not isinstance(return_val, dict):
                        temp_node = {"type": "literal_assignment", "value": return_val}

                    actual_type = _infer_expression_type(temp_node, local_vars, func_def["line"], "return", all_signatures, func_name_context=func_name)
                    if actual_type != expected_return_type:
                        raise ValuaScriptError(ErrorCode.RETURN_TYPE_MISMATCH, line=func_def["line"], name=func_name, provided=actual_type, expected=expected_return_type)

            else:
                line, result_var = step["line"], step["result"]
                if result_var in local_vars:
                    raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE_IN_FUNC, line=line, name=result_var, func_name=func_name)
                rhs_type = _infer_expression_type(step, local_vars, line, result_var, all_signatures, func_name_context=func_name)
                local_vars[result_var] = {"type": rhs_type, "line": line}

        if not has_return:
            raise ValuaScriptError(ErrorCode.MISSING_RETURN_STATEMENT, line=func_def["line"], name=func_name)

    inlined_code = list(execution_steps)
    live_defined_vars = initial_defined_vars.copy()
    call_count = 0
    temp_var_count = 0

    while True:
        made_change_in_pass = False
        i = 0
        while i < len(inlined_code):
            step = inlined_code[i]
            made_change_in_step = False
            if step.get("type") in ("execution_assignment", "multi_assignment"):
                modified_args = []
                for arg in step.get("args", []):
                    if isinstance(arg, dict) and arg.get("function") in user_functions:
                        made_change_in_step = True
                        temp_var_count += 1
                        temp_var_name = f"__temp_{temp_var_count}"

                        nested_call_step = {"line": step["line"], "type": "execution_assignment", **arg}
                        nested_func_def = user_functions[arg.get("function")]
                        if isinstance(nested_func_def["return_type"], list):
                            nested_call_step["type"] = "multi_assignment"
                            num_returns = len(nested_func_def["return_type"])
                            temp_results = [f"{temp_var_name}_{j}" for j in range(num_returns)]
                            nested_call_step["results"] = temp_results
                        else:
                            nested_call_step["result"] = temp_var_name

                        inlined_code.insert(i, nested_call_step)
                        return_types = _infer_expression_type(nested_call_step, live_defined_vars, step["line"], "", all_signatures)
                        if isinstance(return_types, list):
                            for j, r_type in enumerate(return_types):
                                live_defined_vars[temp_results[j]] = {"type": r_type, "line": step["line"]}
                            modified_args.append([Token("CNAME", tr) for tr in temp_results])
                        else:
                            live_defined_vars[temp_var_name] = {"type": return_types, "line": step["line"]}
                            modified_args.append(Token("CNAME", temp_var_name))

                        i += 1
                    else:
                        modified_args.append(arg)
                if made_change_in_step:
                    made_change_in_pass = True
                    step["args"] = modified_args
            i += 1

        udf_call_index = -1
        for i, step in enumerate(inlined_code):
            if step.get("type") in ("execution_assignment", "multi_assignment") and step.get("function") in user_functions:
                udf_call_index = i
                break

        if udf_call_index == -1 and not made_change_in_pass:
            break

        if udf_call_index != -1:
            made_change_in_pass = True
            step = inlined_code.pop(udf_call_index)
            func_name = step["function"]
            func_def = user_functions[func_name]

            call_count += 1
            mangling_prefix = f"__{func_name}_{call_count}__"
            arg_map = {}
            insertion_point = udf_call_index

            for i, param in enumerate(func_def["params"]):
                mangled_param_name = f"{mangling_prefix}{param['name']}"
                param_assign_step = {"result": mangled_param_name, "type": "execution_assignment", "function": "identity", "args": [step["args"][i]], "line": step["line"]}
                inlined_code.insert(insertion_point, param_assign_step)
                live_defined_vars[mangled_param_name] = {"type": param["type"], "line": step["line"]}
                arg_map[param["name"]] = Token("CNAME", mangled_param_name)
                insertion_point += 1

            param_names = {p["name"] for p in func_def["params"]}
            local_var_names = {s["result"] for s in func_def["body"] if s.get("type") not in ("return_statement")}

            def mangle_expression(expr):
                if isinstance(expr, Token):
                    var_name = str(expr)
                    if var_name in param_names:
                        return arg_map[var_name]
                    if var_name in local_var_names:
                        return Token("CNAME", f"{mangling_prefix}{var_name}")
                elif isinstance(expr, dict):
                    new_expr = expr.copy()
                    if "args" in new_expr:
                        new_expr["args"] = [mangle_expression(a) for a in new_expr["args"]]
                    if "results" in new_expr:
                        new_expr["results"] = [f"{mangling_prefix}{r}" for r in new_expr["results"]]
                    if "result" in new_expr:
                        new_expr["result"] = f"{mangling_prefix}{new_expr['result']}"
                    if new_expr.get("type") == "conditional_expression":
                        new_expr["condition"] = mangle_expression(new_expr["condition"])
                        new_expr["then_expr"] = mangle_expression(new_expr["then_expr"])
                        new_expr["else_expr"] = mangle_expression(new_expr["else_expr"])
                    return new_expr
                elif isinstance(expr, list):
                    return [mangle_expression(e) for e in expr]
                return expr

            for body_step in func_def["body"]:
                if body_step.get("type") == "return_statement":
                    if "values" in body_step:
                        mangled_return_values = mangle_expression(body_step["values"])
                        for i, res_var in enumerate(step["results"]):
                            final_assignment = {"result": res_var, "line": step["line"], "type": "execution_assignment", "function": "identity", "args": [mangled_return_values[i]]}
                            inlined_code.insert(insertion_point, final_assignment)
                            insertion_point += 1
                    else:
                        mangled_return_value = mangle_expression(body_step["value"])
                        final_assignment = {"result": step["result"], "line": step["line"]}
                        if isinstance(mangled_return_value, dict) and mangled_return_value.get("type") == "conditional_expression":
                            final_assignment.update(mangled_return_value)
                        elif isinstance(mangled_return_value, dict):
                            final_assignment.update({"type": "execution_assignment", **mangled_return_value})
                        elif isinstance(mangled_return_value, Token):
                            final_assignment.update({"type": "execution_assignment", "function": "identity", "args": [mangled_return_value]})
                        else:
                            final_assignment.update({"type": "literal_assignment", "value": mangled_return_value})
                        inlined_code.insert(insertion_point, final_assignment)
                        insertion_point += 1
                else:
                    mangled_step = mangle_expression(body_step)
                    inlined_code.insert(insertion_point, mangled_step)
                    res_vars = mangled_step.get("results") or [mangled_step.get("result")]
                    rhs_types = _infer_expression_type(mangled_step, live_defined_vars, mangled_step["line"], "", all_signatures, func_name)
                    if not isinstance(rhs_types, list):
                        rhs_types = [rhs_types]
                    for i, r_var in enumerate(res_vars):
                        live_defined_vars[r_var] = {"type": rhs_types[i], "line": mangled_step["line"]}
                    insertion_point += 1

    return inlined_code


def validate_semantics(main_ast, all_user_functions, is_preview_mode, file_path=None):
    """Performs all semantic validation for a runnable script or a module file."""
    execution_steps = main_ast.get("execution_steps", [])
    directives = {}
    is_module = any(d["name"] == "module" for d in main_ast.get("directives", []))

    for d in main_ast.get("directives", []):
        name, line = d["name"], d["line"]
        if name not in DIRECTIVE_CONFIG:
            raise ValuaScriptError(ErrorCode.UNKNOWN_DIRECTIVE, line=line, name=name)
        if name in directives and not is_preview_mode:
            raise ValuaScriptError(ErrorCode.DUPLICATE_DIRECTIVE, line=line, name=name)
        config = DIRECTIVE_CONFIG[name]
        if not config["value_allowed"] and d["value"] is not True:
            raise ValuaScriptError(ErrorCode.MODULE_WITH_VALUE, line=line)
        directives[name] = d

    udf_signatures = {name: {"variadic": False, "arg_types": [p["type"] for p in fdef["params"]], "return_type": fdef["return_type"]} for name, fdef in all_user_functions.items()}
    all_signatures = {**FUNCTION_SIGNATURES, **udf_signatures}

    if is_module:
        if execution_steps:
            raise ValuaScriptError(ErrorCode.GLOBAL_LET_IN_MODULE, line=execution_steps[0]["line"])
        for name, d in directives.items():
            if not DIRECTIVE_CONFIG[name]["allowed_in_module"]:
                raise ValuaScriptError(ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, line=d["line"], name=name)
        RESERVED_NAMES = set(FUNCTION_SIGNATURES.keys())
        for name, func_def in all_user_functions.items():
            if name in RESERVED_NAMES:
                raise ValuaScriptError(ErrorCode.REDEFINE_BUILTIN_FUNCTION, line=func_def["line"], name=name)
        _check_for_recursive_calls(all_user_functions)
        module_functions = {f["name"]: f for f in main_ast.get("function_definitions", [])}
        validate_and_inline_udfs([], module_functions, all_signatures, initial_defined_vars={})
        return [], {}, {}, None

    if not is_preview_mode:
        for name, config in DIRECTIVE_CONFIG.items():
            if name in ["import", "module"]:
                continue
            is_req = config["required"](directives) if callable(config["required"]) else config["required"]
            if is_req and name not in directives:
                code = ErrorCode.MISSING_ITERATIONS_DIRECTIVE if name == "iterations" else ErrorCode.MISSING_OUTPUT_DIRECTIVE
                raise ValuaScriptError(code)

    RESERVED_NAMES = set(FUNCTION_SIGNATURES.keys())
    for name, func_def in all_user_functions.items():
        if name in RESERVED_NAMES:
            raise ValuaScriptError(ErrorCode.REDEFINE_BUILTIN_FUNCTION, line=func_def["line"], name=name)
    _check_for_recursive_calls(all_user_functions)

    defined_vars = {}
    for step in execution_steps:
        line = step["line"]

        # Check for duplicate variables before defining them
        if step.get("type") == "multi_assignment":
            for r in step["results"]:
                if r in defined_vars:
                    raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE, line=line, name=r)
            if len(set(step["results"])) != len(step["results"]):
                raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE, line=line, name="a variable in the same assignment")

        else:  # Single assignment
            if step["result"] in defined_vars:
                raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE, line=line, name=step["result"])

        # Check for assignment arity mismatch
        if "function" in step:
            func_name = step["function"]
            if func_name not in all_signatures:
                raise ValuaScriptError(ErrorCode.UNKNOWN_FUNCTION, line=line, name=func_name)
            return_type = all_signatures[func_name]["return_type"]
            is_multi_return = isinstance(return_type, list)

            if step.get("type") == "multi_assignment":
                if not is_multi_return:
                    raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=f"assignment for '{func_name}'", expected=1, provided=len(step["results"]))
                if len(step["results"]) != len(return_type):
                    raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=f"assignment for '{func_name}'", expected=len(return_type), provided=len(step["results"]))
            else:  # Single assignment
                if is_multi_return:
                    raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=f"assignment for '{func_name}'", expected=len(return_type), provided=1)

        # Infer types and add to defined_vars
        if step.get("type") == "multi_assignment":
            rhs_types = _infer_expression_type(step, defined_vars, line, "", all_signatures)
            for i, result_var in enumerate(step["results"]):
                defined_vars[result_var] = {"type": rhs_types[i], "line": line}
        else:
            rhs_type = _infer_expression_type(step, defined_vars, line, step["result"], all_signatures)
            defined_vars[step["result"]] = {"type": rhs_type, "line": line}

    inlined_steps = validate_and_inline_udfs(execution_steps, all_user_functions, all_signatures, initial_defined_vars=defined_vars)

    final_defined_vars = {}
    for step in inlined_steps:
        line = step["line"]
        if step.get("type") == "multi_assignment":
            results = step["results"]
            rhs_types = _infer_expression_type(step, final_defined_vars, line, "", all_signatures)
            for i, result_var in enumerate(results):
                final_defined_vars[result_var] = {"type": rhs_types[i], "line": line}
        else:
            result_var = step["result"]
            if result_var not in final_defined_vars:
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
                if file_path:
                    base_dir = os.path.dirname(file_path)
                    sim_config["output_file"] = os.path.abspath(os.path.join(base_dir, value))
                else:
                    sim_config["output_file"] = value

    if not is_preview_mode and output_var not in final_defined_vars:
        if output_var not in defined_vars:
            raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, name=output_var)

    return inlined_steps, final_defined_vars, sim_config, output_var
