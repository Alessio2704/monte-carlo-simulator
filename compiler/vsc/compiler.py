import os
import sys
from lark import Lark, Transformer, Token
from collections import deque

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
        return {"name": str(items[0]), "value": items[1], "line": items[0].line}

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

    def start(self, children):
        return {"directives": [i for i in children if isinstance(i, dict) and "name" in i], "execution_steps": [i for i in children if isinstance(i, dict) and "result" in i]}


# ==============================================================================
# HELPER FUNCTIONS FOR DEPENDENCY ANALYSIS AND OPTIMIZATION
# ==============================================================================


def _get_dependencies_from_arg(arg):
    """Recursively find all variable dependencies within a single argument."""
    deps = set()
    if isinstance(arg, Token):
        deps.add(str(arg))
    elif isinstance(arg, dict) and "args" in arg:
        for sub_arg in arg["args"]:
            deps.update(_get_dependencies_from_arg(sub_arg))
    return deps


def _build_dependency_graph(execution_steps):
    """
    Builds two graphs:
    1. dependencies: maps a variable to the set of variables it depends on.
    2. dependents: maps a variable to the set of variables that depend on it.
    """
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

    # Build the reverse graph (dependents)
    for var, deps in dependencies.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].add(var)

    return dependencies, dependents


def _find_stochastic_variables(execution_steps, dependents):
    """
    Performs taint analysis to find all variables that depend on a stochastic source.
    """
    stochastic_vars = set()
    queue = deque()

    def _expression_is_stochastic(expression_dict):
        """Recursively checks if any function call within an expression is stochastic."""
        if not isinstance(expression_dict, dict):
            return False
        func_name = expression_dict.get("function")
        if func_name and FUNCTION_SIGNATURES.get(func_name, {}).get("is_stochastic", False):
            return True
        for arg in expression_dict.get("args", []):
            if _expression_is_stochastic(arg):
                return True
        return False

    # 1. Find initial sources of stochasticity by recursively checking expressions
    for step in execution_steps:
        if step.get("type") == "execution_assignment":
            if _expression_is_stochastic(step):
                var_name = step["result"]
                if var_name not in stochastic_vars:
                    stochastic_vars.add(var_name)
                    queue.append(var_name)

    # 2. Propagate the stochastic "taint" through the dependency graph
    while queue:
        current_var = queue.popleft()
        for dependent_var in dependents.get(current_var, []):
            if dependent_var not in stochastic_vars:
                stochastic_vars.add(dependent_var)
                queue.append(dependent_var)

    return stochastic_vars


def _topological_sort_steps(steps, dependencies):
    """
    Sorts a list of execution steps based on their dependencies to ensure
    correct calculation order.
    """
    step_map = {step["result"]: step for step in steps}
    sorted_vars = []
    visited = set()
    recursion_stack = set()

    def visit(var):
        visited.add(var)
        recursion_stack.add(var)
        for dep in dependencies.get(var, []):
            if dep in recursion_stack:
                # This should ideally be caught earlier, but serves as a safeguard.
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


def validate_valuascript(script_content: str, context="cli"):
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

    # --- Stage 1: Parsing and Transformation ---
    parse_tree = LARK_PARSER.parse(script_content)
    raw_recipe = ValuaScriptTransformer().transform(parse_tree)

    # --- Stage 2: Process Directives and Basic Config ---
    raw_directives_list = raw_recipe.get("directives", [])
    seen_directives, directives = set(), {}
    for d in raw_directives_list:
        name = d["name"]
        if name not in DIRECTIVE_CONFIG:
            raise ValuaScriptError(f"L{d['line']}: Unknown directive '@{name}'.")
        if name in seen_directives:
            raise ValuaScriptError(f"L{d['line']}: The directive '@{name}' is defined more than once.")
        seen_directives.add(name)
        directives[name] = d

    sim_config, output_var = {}, ""
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

    # --- Stage 3: Type Inference and Semantic Validation ---
    defined_vars, used_vars = {}, set()
    for step in raw_recipe["execution_steps"]:
        line, result_var = step["line"], step["result"]
        if result_var in defined_vars:
            raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once.")
        rhs_type = _infer_expression_type(step, defined_vars, used_vars, line, result_var)
        defined_vars[result_var] = {"type": rhs_type, "line": line}

    if output_var not in defined_vars:
        line = directives["output"]["line"]
        raise ValuaScriptError(f"L{line}: The final @output variable '{output_var}' is not defined.")

    all_defined = set(defined_vars.keys())
    unused = all_defined - used_vars
    if output_var in unused:
        unused.remove(output_var)
    if unused and context != "lsp":
        print(f"\n{TerminalColors.YELLOW}--- Compiler Warnings ---{TerminalColors.RESET}")
        for var in sorted(list(unused)):
            line_num = defined_vars[var]["line"]
            print(f"{TerminalColors.YELLOW}Warning: Variable '{var}' was defined on line {line_num} but was never used.{TerminalColors.RESET}")

    # --- Stage 4: Loop-Invariant Code Motion Optimization ---
    if context != "lsp":
        print(f"\n--- Running Compiler Optimizations ---")

    dependencies, dependents = _build_dependency_graph(raw_recipe["execution_steps"])
    stochastic_vars = _find_stochastic_variables(raw_recipe["execution_steps"], dependents)

    pre_trial_steps_raw, per_trial_steps_raw = [], []
    for step in raw_recipe["execution_steps"]:
        if step["result"] in stochastic_vars:
            per_trial_steps_raw.append(step)
        else:
            pre_trial_steps_raw.append(step)

    # Ensure correct execution order within the pre-trial phase
    pre_trial_dependencies = {k: v for k, v in dependencies.items() if k in {s["result"] for s in pre_trial_steps_raw}}
    pre_trial_steps = _topological_sort_steps(pre_trial_steps_raw, pre_trial_dependencies)

    if context != "lsp":
        print(f"Optimization complete: Moved {len(pre_trial_steps)} deterministic step(s) to the pre-trial phase.")

    # --- Stage 5: Final JSON Recipe Generation ---
    def _process_arg_for_json(arg):
        if isinstance(arg, _StringLiteral):
            return {"type": "string_literal", "value": arg.value}
        if isinstance(arg, Token):
            return str(arg)
        if isinstance(arg, dict) and "args" in arg:
            arg["args"] = [_process_arg_for_json(a) for a in arg["args"]]
        return arg

    for step in pre_trial_steps + per_trial_steps_raw:  # Use raw per_trial, as its order is already correct
        if "value" in step:
            if isinstance(step.get("value"), Token):
                step["value"] = str(step["value"])
            elif isinstance(step.get("value"), _StringLiteral):
                step["value"] = step["value"].value
        if "args" in step:
            step["args"] = [_process_arg_for_json(a) for a in step["args"]]
        if "line" in step:
            del step["line"]

    return {
        "simulation_config": sim_config,
        "output_variable": output_var,
        "pre_trial_steps": pre_trial_steps,
        "per_trial_steps": per_trial_steps_raw,
    }


def _infer_expression_type(expression_dict, defined_vars, used_vars, line_num, current_result_var):
    expr_type = expression_dict.get("type")
    if expr_type == "literal_assignment":
        value = expression_dict.get("value")
        if isinstance(value, (int, float)):
            return "scalar"
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, (int, float)):
                    error_val = f'"{item.value}"' if isinstance(item, _StringLiteral) else str(item)
                    raise ValuaScriptError(f"L{line_num}: Invalid item {error_val} in vector literal for '{current_result_var}'. Only literal numbers are allowed in vectors.")
            return "vector"
        if isinstance(value, _StringLiteral):
            return "string"
        raise ValuaScriptError(f"L{line_num}: Invalid value for '{current_result_var}'.")

    if expr_type == "execution_assignment":
        func_name = expression_dict["function"]
        args = expression_dict.get("args", [])
        if func_name not in FUNCTION_SIGNATURES:
            raise ValuaScriptError(f"L{line_num}: Unknown function '{func_name}'.")
        signature = FUNCTION_SIGNATURES[func_name]
        if not signature.get("variadic", False) and len(args) != len(signature["arg_types"]):
            raise ValuaScriptError(f"L{line_num}: Function '{func_name}' expects {len(signature['arg_types'])} argument(s), but got {len(args)}.")

        inferred_arg_types = []
        for arg in args:
            arg_type = None
            if isinstance(arg, Token):
                var_name = str(arg)
                used_vars.add(var_name)
                if var_name not in defined_vars:
                    raise ValuaScriptError(f"L{line_num}: Variable '{var_name}' used in function '{func_name}' is not defined.")
                arg_type = defined_vars[var_name]["type"]
            elif isinstance(arg, _StringLiteral):
                arg_type = "string"
            else:
                temp_dict = {"type": "execution_assignment", **arg} if isinstance(arg, dict) else {"type": "literal_assignment", "value": arg}
                arg_type = _infer_expression_type(temp_dict, defined_vars, used_vars, line_num, current_result_var)
            inferred_arg_types.append(arg_type)

        if not signature.get("variadic"):
            for i, expected_type in enumerate(signature["arg_types"]):
                if expected_type != "any" and expected_type != inferred_arg_types[i]:
                    raise ValuaScriptError(f"L{line_num}: Argument {i+1} for '{func_name}' expects a '{expected_type}', but got a '{inferred_arg_types[i]}'.")

        return_type_rule = signature["return_type"]
        return return_type_rule(inferred_arg_types) if callable(return_type_rule) else return_type_rule
    raise ValuaScriptError(f"L{line_num}: Could not determine type for '{current_result_var}'.")