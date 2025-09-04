import os
import sys
from lark import Lark, Transformer, Token
from collections import deque
from textwrap import dedent

from .exceptions import ValuaScriptError
from .utils import TerminalColors
from .config import DIRECTIVE_CONFIG, FUNCTION_SIGNATURES, OPERATOR_MAP

LARK_PARSER = None
try:
    from importlib.resources import files as pkg_files

    valuasc_grammar = (pkg_files("vsc") / "valuascript.lark").read_text()
    LARK_PARSER = Lark(valuasc_grammar, start="start", parser="earley")
except Exception:
    # Fallback for older python or different dev environments
    grammar_path = os.path.join(os.path.dirname(__file__), "valuascript.lark")
    with open(grammar_path, "r") as f:
        valuasc_grammar = f.read()
    LARK_PARSER = Lark(valuasc_grammar, start="start", parser="earley")


class _StringLiteral:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'StringLiteral("{self.value}")'


class ValuaScriptTransformer(Transformer):
    def STRING(self, s):
        return _StringLiteral(s.value[1:-1])

    def DOCSTRING(self, s):
        # Remove the triple quotes and dedent the string
        content = s.value[3:-3]
        return dedent(content).strip()

    def infix_expression(self, items):
        if len(items) == 1:
            return items[0]
        tree, i = items[0], 1
        while i < len(items):
            op, right = items[i], items[i + 1]
            func_name = OPERATOR_MAP[op.value]
            if isinstance(tree, dict) and tree.get("function") == func_name and func_name in ("add", "multiply"):
                tree["args"].append(right)
            else:
                tree = {"function": func_name, "args": [tree, right]}
            i += 2
        return tree

    def expression(self, i):
        return i[0]

    def term(self, i):
        return i[0]

    def factor(self, i):
        return i[0]

    def power(self, i):
        return i[0]

    def atom(self, i):
        return i[0]

    def arg(self, i):
        return i[0]

    def SIGNED_NUMBER(self, n):
        val = n.value.replace("_", "")
        return float(val) if "." in val or "e" in val.lower() else int(val)

    def CNAME(self, c):
        return c

    def function_call(self, items):
        func_name_token = items[0]
        args = [item for item in items[1:] if item is not None]
        return {"function": str(func_name_token), "args": args}

    def vector(self, items):
        return [item for item in items if item is not None]

    def element_access(self, items):
        var_token, index_expression = items
        return {"function": "get_element", "args": [var_token, index_expression]}

    def delete_element_vector(self, items):
        var_token, end_expression = items
        return {"function": "delete_element", "args": [var_token, end_expression]}

    def directive_setting(self, items):
        return {"type": "directive", "name": str(items[0]), "value": items[1], "line": items[0].line}

    def assignment(self, items):
        _let_token, var_token, expression = items
        base_step = {"result": str(var_token), "line": var_token.line}
        if isinstance(expression, dict):
            base_step.update({"type": "execution_assignment", **expression})
        elif isinstance(expression, Token):
            base_step.update({"type": "execution_assignment", "function": "identity", "args": [expression]})
        else:
            base_step.update({"type": "literal_assignment", "value": expression})
        return base_step

    def function_body(self, items):
        return items

    def function_def(self, items):
        func_name_token = items[0]
        body_list = items[-1]

        # Based on the grammar, the item at index -2 is the docstring (or None if absent)
        # and the item at -3 is the return type.
        docstring = items[-2]
        return_type_token = items[-3]
        params = items[1:-3]

        return {
            "type": "function_definition",
            "name": str(func_name_token),
            "params": [p for p in params if isinstance(p, dict)],
            "return_type": str(return_type_token),
            "body": body_list,
            "docstring": docstring,
            "line": func_name_token.line,
        }

    def param(self, items):
        return {"name": str(items[0]), "type": str(items[1])}

    def return_statement(self, items):
        return {"type": "return_statement", "value": items[0]}

    def start(self, children):
        return {
            "directives": [i for i in children if i.get("type") == "directive"],
            "execution_steps": [i for i in children if i.get("type") in ("execution_assignment", "literal_assignment")],
            "function_definitions": [i for i in children if i.get("type") == "function_definition"],
        }


# ==============================================================================
# HELPER FUNCTIONS FOR DEPENDENCY ANALYSIS AND OPTIMIZATION
# ==============================================================================


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


def _find_live_variables(output_var, dependencies):
    live_vars = set()
    queue = deque([output_var])
    while queue:
        current_var = queue.popleft()
        if current_var not in live_vars:
            live_vars.add(current_var)
            for dep in dependencies.get(current_var, []):
                queue.append(dep)
    return live_vars


def _get_dependencies_from_arg(arg):
    deps = set()
    if isinstance(arg, Token):
        deps.add(str(arg))
    elif isinstance(arg, dict) and "args" in arg:
        for sub_arg in arg["args"]:
            deps.update(_get_dependencies_from_arg(sub_arg))
    return deps


def _build_dependency_graph(execution_steps):
    dependencies = {}
    dependents = {step["result"]: set() for step in execution_steps}

    for step in execution_steps:
        var_name = step["result"]
        current_deps = set()
        if step.get("type") == "execution_assignment":
            for arg in step.get("args", []):
                dep_vars = _get_dependencies_from_arg(arg)
                current_deps.update(dep_vars)
        dependencies[var_name] = current_deps

    for var, deps in dependencies.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].add(var)

    return dependencies, dependents


def _find_stochastic_variables(execution_steps, dependents):
    stochastic_vars = set()
    queue = deque()

    def _expression_is_stochastic(expression_dict):
        if not isinstance(expression_dict, dict):
            return False
        func_name = expression_dict.get("function")
        if func_name and FUNCTION_SIGNATURES.get(func_name, {}).get("is_stochastic", False):
            return True
        for arg in expression_dict.get("args", []):
            if _expression_is_stochastic(arg):
                return True
        return False

    for step in execution_steps:
        if step.get("type") == "execution_assignment":
            if _expression_is_stochastic(step):
                var_name = step["result"]
                if var_name not in stochastic_vars:
                    stochastic_vars.add(var_name)
                    queue.append(var_name)

    while queue:
        current_var = queue.popleft()
        for dependent_var in dependents.get(current_var, []):
            if dependent_var not in stochastic_vars:
                stochastic_vars.add(dependent_var)
                queue.append(dependent_var)

    return stochastic_vars


def _topological_sort_steps(steps, dependencies):
    step_map = {step["result"]: step for step in steps}
    sorted_vars = []
    visited = set()
    recursion_stack = set()

    def visit(var):
        visited.add(var)
        recursion_stack.add(var)
        for dep in dependencies.get(var, []):
            if dep in recursion_stack:
                raise ValuaScriptError(f"Circular dependency detected involving variable '{var}'.")
            if dep not in visited and dep in step_map:
                visit(dep)
        recursion_stack.remove(var)
        sorted_vars.append(var)

    for step in steps:
        var_name = step["result"]
        if var_name not in visited:
            visit(var_name)

    return [step_map[var] for var in sorted_vars]


def _inline_and_mangle_functions(execution_steps, user_functions):
    inlined_code = execution_steps
    call_count = 0
    temp_var_count = 0

    while True:
        contains_udf_call = any(s.get("type") == "execution_assignment" and s.get("function") in user_functions for s in inlined_code)
        contains_nested_udf_call = any(isinstance(arg, dict) and arg.get("function") in user_functions for s in inlined_code if s.get("type") == "execution_assignment" for arg in s.get("args", []))

        if not contains_udf_call and not contains_nested_udf_call:
            break

        # --- FLATTENING PASS: Hoist nested UDF calls into their own 'let' statements ---
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
                call_count += 1
                func_name = step["function"]
                func_def = user_functions[func_name]
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


def validate_valuascript(script_content: str, context="cli", optimize=False, verbose=False, preview_variable=None):
    if preview_variable:
        optimize = True

    if context == "lsp" and not script_content.strip():
        return None
    for i, line in enumerate(script_content.splitlines()):
        clean_line = line.split("#", 1)[0].strip()
        if not clean_line:
            continue
        if clean_line.count("(") != clean_line.count(")"):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Unmatched opening parenthesis.")
        if clean_line.count("[") != clean_line.count("]"):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Unmatched opening bracket.")
        if (clean_line.startswith("let") or clean_line.startswith("@")) and clean_line.endswith("="):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Missing value after '='.")
        if clean_line.startswith("let") and "=" not in clean_line:
            if len(clean_line.split()) > 0 and clean_line.split()[0] == "let":
                raise ValuaScriptError(f"L{i+1}: Syntax Error: Incomplete assignment.")

    parse_tree = LARK_PARSER.parse(script_content)
    raw_recipe = ValuaScriptTransformer().transform(parse_tree)

    user_functions = {f["name"]: f for f in raw_recipe.get("function_definitions", [])}
    execution_steps = raw_recipe.get("execution_steps", [])

    _check_for_recursive_calls(user_functions)

    udf_signatures = {}
    for func_name, func_def in user_functions.items():
        if func_name in FUNCTION_SIGNATURES:
            raise ValuaScriptError(f"L{func_def['line']}: Cannot redefine built-in function '{func_name}'.")
        udf_signatures[func_name] = {"variadic": False, "arg_types": [p["type"] for p in func_def["params"]], "return_type": func_def["return_type"]}
    all_signatures = {**FUNCTION_SIGNATURES, **udf_signatures}

    for func_name, func_def in user_functions.items():
        local_vars = {p["name"]: {"type": p["type"], "line": func_def["line"]} for p in func_def["params"]}
        has_return = False
        for step in func_def["body"]:
            if step.get("type") == "return_statement":
                has_return = True
                return_type = _infer_expression_type({"type": "execution_assignment", "function": "identity", "args": [step["value"]]}, local_vars, set(), func_def["line"], "return", all_signatures)
                if return_type != func_def["return_type"]:
                    raise ValuaScriptError(f"L{func_def['line']}: Function '{func_name}' returns type '{return_type}' but is defined to return '{func_def['return_type']}'.")
            else:
                line, result_var = step["line"], step["result"]
                if result_var in local_vars:
                    raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once in function '{func_name}'.")
                rhs_type = _infer_expression_type(step, local_vars, set(), line, result_var, all_signatures)
                local_vars[result_var] = {"type": rhs_type, "line": line}
        if not has_return:
            raise ValuaScriptError(f"L{func_def['line']}: Function '{func_name}' is missing a return statement.")

    defined_vars = {}
    for step in execution_steps:
        line, result_var = step["line"], step["result"]
        if result_var in defined_vars:
            raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once.")
        rhs_type = _infer_expression_type(step, defined_vars, set(), line, result_var, all_signatures)
        defined_vars[result_var] = {"type": rhs_type, "line": line}

    raw_directives_list = raw_recipe.get("directives", [])
    seen_directives, directives = set(), {}
    for d in raw_directives_list:
        name = d["name"]
        if name not in DIRECTIVE_CONFIG:
            raise ValuaScriptError(f"L{d['line']}: Unknown directive '@{name}'.")
        if name in seen_directives and not preview_variable:
            raise ValuaScriptError(f"L{d['line']}: The directive '@{name}' is defined more than once.")
        seen_directives.add(name)
        directives[name] = d

    sim_config, output_var = {}, ""
    if preview_variable:
        output_var = preview_variable
        if "output_file" in directives:
            raw_value = directives["output_file"]["value"]
            if isinstance(raw_value, _StringLiteral):
                sim_config["output_file"] = raw_value.value
    else:
        for name, config in DIRECTIVE_CONFIG.items():
            if config["required"] and name not in directives:
                raise ValuaScriptError(config["error_missing"])
            if name in directives:
                d = directives[name]
                raw_value = d["value"]
                if config["type"] is str and name == "output_file" and not isinstance(raw_value, _StringLiteral):
                    raise ValuaScriptError(f"L{d['line']}: {config['error_type']}")
                elif config["type"] is str and name == "output" and not isinstance(raw_value, Token):
                    raise ValuaScriptError(f"L{d['line']}: {config['error_type']}")
                value_for_validation = raw_value.value if isinstance(raw_value, _StringLiteral) else (str(raw_value) if isinstance(raw_value, Token) else raw_value)
                if config["type"] is int and not isinstance(value_for_validation, int):
                    raise ValuaScriptError(f"L{d['line']}: {config['error_type']}")
                if name == "iterations":
                    sim_config["num_trials"] = value_for_validation
                elif name == "output":
                    output_var = value_for_validation
                elif name == "output_file":
                    sim_config["output_file"] = value_for_validation
        if not output_var:
            raise ValuaScriptError(DIRECTIVE_CONFIG["output"]["error_missing"])

    if output_var not in defined_vars:
        raise ValuaScriptError(f"The final @output variable '{output_var}' is not defined.")

    inlined_steps = _inline_and_mangle_functions(execution_steps, user_functions)
    raw_recipe["execution_steps"] = inlined_steps

    all_original_vars = {step["result"] for step in raw_recipe["execution_steps"]}
    dependencies, dependents = _build_dependency_graph(raw_recipe["execution_steps"])

    if optimize:
        live_variables = _find_live_variables(output_var, dependencies)
        if verbose:
            print("\n--- Running Dead Code Elimination ---")
        original_step_count = len(raw_recipe["execution_steps"])
        raw_recipe["execution_steps"] = [step for step in raw_recipe["execution_steps"] if step["result"] in live_variables]
        removed_count = original_step_count - len(raw_recipe["execution_steps"])
        if removed_count > 0 and verbose:
            removed_vars = sorted(list(all_original_vars - live_variables))
            print(f"Optimization complete: Removed {removed_count} unused variable(s): {', '.join(removed_vars)}")
        elif verbose:
            print("Optimization complete: No unused variables found to remove.")
        dependencies, dependents = _build_dependency_graph(raw_recipe["execution_steps"])
    else:
        unused_vars = all_original_vars - _find_live_variables(output_var, dependencies)
        if unused_vars and context != "lsp":
            pass

    if verbose:
        print(f"\n--- Running Compiler Optimizations ---")

    stochastic_vars = _find_stochastic_variables(raw_recipe["execution_steps"], dependents)

    if preview_variable:
        is_stochastic = preview_variable in stochastic_vars
        sim_config["num_trials"] = 100 if is_stochastic else 1

    pre_trial_steps_raw, per_trial_steps_raw = [], []
    for step in raw_recipe["execution_steps"]:
        if step["result"] in stochastic_vars:
            per_trial_steps_raw.append(step)
        else:
            pre_trial_steps_raw.append(step)

    pre_trial_dependencies = {k: v for k, v in dependencies.items() if k in {s["result"] for s in pre_trial_steps_raw}}
    pre_trial_steps = _topological_sort_steps(pre_trial_steps_raw, pre_trial_dependencies)

    if verbose and pre_trial_steps:
        moved_vars = sorted([step["result"] for step in pre_trial_steps])
        print(f"Optimization complete: Moved {len(pre_trial_steps)} deterministic step(s) to the pre-trial phase: {', '.join(moved_vars)}")

    def _process_arg_for_json(arg):
        if isinstance(arg, _StringLiteral):
            return {"type": "string_literal", "value": arg.value}
        if isinstance(arg, Token):
            return str(arg)
        if isinstance(arg, dict) and "args" in arg:
            arg["args"] = [_process_arg_for_json(a) for a in arg["args"]]
        return arg

    for step in pre_trial_steps + per_trial_steps_raw:
        if "value" in step:
            if isinstance(step.get("value"), Token):
                step["value"] = str(step["value"])
            elif isinstance(step.get("value"), _StringLiteral):
                step["value"] = step["value"].value
        if "args" in step:
            step["args"] = [_process_arg_for_json(a) for a in step["args"]]
    return {"simulation_config": sim_config, "output_variable": output_var, "pre_trial_steps": pre_trial_steps, "per_trial_steps": per_trial_steps_raw}


def _infer_expression_type(expression_dict, defined_vars, used_vars, line_num, current_result_var, all_signatures={}):
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
                arg_type = _infer_expression_type(temp_dict, defined_vars, used_vars, line_num, current_result_var, all_signatures)
            inferred_arg_types.append(arg_type)

        if not signature.get("variadic"):
            for i, expected_type in enumerate(signature["arg_types"]):
                if expected_type != "any" and expected_type != inferred_arg_types[i]:
                    raise ValuaScriptError(f"L{line_num}: Argument {i+1} for '{func_name}' expects a '{expected_type}', but got a '{inferred_arg_types[i]}'.")

        return_type_rule = signature["return_type"]
        return return_type_rule(inferred_arg_types) if callable(return_type_rule) else return_type_rule

    raise ValuaScriptError(f"L{line_num}: Could not determine type for '{current_result_var}'.")
