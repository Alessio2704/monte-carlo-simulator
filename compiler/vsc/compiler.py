import os
import sys
from lark import Lark, Transformer, Token
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken

from .exceptions import ValuaScriptError
from .utils import TerminalColors, format_lark_error
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
        val = n.value
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
        # Corresponds to the rule: CNAME "[" ":" expression "]"
        var_token, end_expression = items
        return {"function": "delete_element", "args": [var_token, end_expression]}

    def directive_setting(self, items):
        return {"name": str(items[0]), "value": items[1], "line": items[0].line}

    def assignment(self, items):
        # Correctly unpacks [LET_TOKEN, CNAME_TOKEN, expression_result]
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

    parse_tree = LARK_PARSER.parse(script_content)
    raw_recipe = ValuaScriptTransformer().transform(parse_tree)

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
    if unused:
        print(f"\n{TerminalColors.YELLOW}--- Compiler Warnings ---{TerminalColors.RESET}")
        for var in sorted(list(unused)):
            line_num = defined_vars[var]["line"]
            print(f"{TerminalColors.YELLOW}Warning: Variable '{var}' was defined on line {line_num} but was never used.{TerminalColors.RESET}")

    def _process_arg_for_json(arg):
        if isinstance(arg, _StringLiteral):
            return {"type": "string_literal", "value": arg.value}
        if isinstance(arg, Token):
            return str(arg)
        if isinstance(arg, dict) and "args" in arg:
            arg["args"] = [_process_arg_for_json(a) for a in arg["args"]]
        return arg

    for step in raw_recipe["execution_steps"]:
        if "value" in step:
            if isinstance(step.get("value"), Token):
                step["value"] = str(step["value"])
            elif isinstance(step.get("value"), _StringLiteral):
                step["value"] = step["value"].value
        if "args" in step:
            step["args"] = [_process_arg_for_json(a) for a in step["args"]]

    pre_trial_steps, per_trial_steps = [], []
    for step in raw_recipe["execution_steps"]:
        if step.get("type") == "literal_assignment":
            per_trial_steps.append(step)
            continue
        func_name = step.get("function")
        if func_name and FUNCTION_SIGNATURES[func_name]["execution_phase"] == "pre_trial":
            pre_trial_steps.append(step)
        else:
            per_trial_steps.append(step)

    for step in pre_trial_steps + per_trial_steps:
        if "line" in step:
            del step["line"]

    return {
        "simulation_config": sim_config,
        "output_variable": output_var,
        "pre_trial_steps": pre_trial_steps,
        "per_trial_steps": per_trial_steps,
    }


def _infer_expression_type(expression_dict, defined_vars, used_vars, line_num, current_result_var):
    expr_type = expression_dict.get("type")
    if expr_type == "literal_assignment":
        value = expression_dict.get("value")
        if isinstance(value, (int, float)):
            return "scalar"
        if isinstance(value, list):
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
