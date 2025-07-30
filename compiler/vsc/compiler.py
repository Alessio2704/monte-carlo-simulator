from lark import Transformer
from lark.lexer import Token

from .exceptions import ValuaScriptError
from .utils import TerminalColors
from .config import DIRECTIVE_CONFIG, FUNCTION_SIGNATURES, OPERATOR_MAP


class _StringLiteral:
    """A wrapper to distinguish string literals from variable names during compilation."""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'StringLiteral("{self.value}")'


class ValuaScriptTransformer(Transformer):
    def STRING(self, s: Token) -> _StringLiteral:
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

    def SIGNED_NUMBER(self, n: Token):
        val = n.value
        return float(val) if "." in val or "e" in val.lower() else int(val)

    def CNAME(self, c: Token) -> Token:
        return c

    def function_call(self, items):
        func_name_token = items[0]
        args = [item for item in items[1:] if item is not None]
        return {"function": str(func_name_token), "args": args}

    def vector(self, items):
        return [item for item in items if item is not None]

    def directive_setting(self, items):
        name_token, value = items
        return {"name": str(name_token), "value": value, "line": name_token.line}

    def assignment(self, items):
        var_token, expression = items
        base_step = {"result": str(var_token), "line": var_token.line}
        # This is the original, correct logic.
        # It correctly identifies `let x = y` as an identity function call.
        if isinstance(expression, dict):
            base_step.update({"type": "execution_assignment", **expression})
        elif isinstance(expression, Token):
            base_step.update({"type": "execution_assignment", "function": "identity", "args": [expression]})
        else:
            base_step.update({"type": "literal_assignment", "value": expression})
        return base_step

    def start(self, children):
        directives = [item for item in children if isinstance(item, dict) and "name" in item]
        assignments = [item for item in children if isinstance(item, dict) and "result" in item]
        return {"directives": directives, "execution_steps": assignments}


def lint_script(script_content: str):
    lines = script_content.splitlines()
    for i, line in enumerate(lines):
        clean_line = line.split("#", 1)[0].strip()
        if not clean_line:
            continue
        if clean_line.count("(") != clean_line.count(")"):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Unmatched opening parenthesis '(' on this line.")
        if clean_line.count("[") != clean_line.count("]"):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Unmatched opening bracket '[' on this line.")
        if clean_line.startswith("let") and clean_line.endswith("="):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Missing value or formula after the equals sign '='.")


def validate_recipe(recipe: dict):
    print("\n--- Running Semantic Validation ---")
    directives = {d["name"]: d for d in recipe.get("directives", [])}
    sim_config, output_var = {}, ""

    for name, config in DIRECTIVE_CONFIG.items():
        if config["required"] and name not in directives:
            raise ValuaScriptError(config["error_missing"])
        if name in directives:
            d = directives[name]
            raw_value = d["value"]

            value_for_validation = raw_value
            if isinstance(raw_value, _StringLiteral):
                value_for_validation = raw_value.value
            elif isinstance(raw_value, Token):
                value_for_validation = str(raw_value)

            if not isinstance(value_for_validation, config["type"]):
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
    for step in recipe["execution_steps"]:
        line, result_var = step["line"], step["result"]
        if result_var in defined_vars:
            raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once.")
        rhs_type = infer_expression_type(step, defined_vars, used_vars, line, result_var)
        defined_vars[result_var] = {"type": rhs_type, "line": line}

    if output_var not in defined_vars:
        raise ValuaScriptError(f"The final @output variable '{output_var}' is not defined.")
    print(f"Found {len(defined_vars)} defined variables. Type inference successful.")

    all_defined = set(defined_vars.keys())
    unused = all_defined - used_vars
    if output_var in unused:
        unused.remove(output_var)
    if unused:
        print(f"\n{TerminalColors.YELLOW}--- Compiler Warnings ---{TerminalColors.RESET}")
        for var in sorted(list(unused)):
            line_num = defined_vars[var]["line"]
            print(f"{TerminalColors.YELLOW}Warning: Variable '{var}' was defined on line {line_num} but was never used.{TerminalColors.RESET}")

    print(f"{TerminalColors.GREEN}--- Validation Successful ---{TerminalColors.RESET}")

    # --- Clean up step values for JSON output ---
    def _process_arg_for_json(arg):
        if isinstance(arg, _StringLiteral):
            return {"type": "string_literal", "value": arg.value}
        if isinstance(arg, Token):
            return str(arg)
        if isinstance(arg, dict) and "args" in arg:
            arg["args"] = [_process_arg_for_json(a) for a in arg["args"]]
        return arg

    for step in recipe["execution_steps"]:
        if "value" in step:
            if isinstance(step.get("value"), Token):
                step["value"] = str(step["value"])
            elif isinstance(step.get("value"), _StringLiteral):
                # This handles `let x = "string"`
                step["value"] = step["value"].value
        if "args" in step:
            step["args"] = [_process_arg_for_json(a) for a in step["args"]]

    # --- Partition steps into pre-trial and per-trial phases ---
    pre_trial_steps = []
    per_trial_steps = []
    for step in recipe["execution_steps"]:
        if step.get("type") == "literal_assignment":
            per_trial_steps.append(step)
            continue

        func_name = step.get("function")
        if func_name and FUNCTION_SIGNATURES[func_name]["execution_phase"] == "pre_trial":
            pre_trial_steps.append(step)
        else:
            per_trial_steps.append(step)

    # Clean the line numbers from the final output
    for step in pre_trial_steps + per_trial_steps:
        if "line" in step:
            del step["line"]

    return {
        "simulation_config": sim_config,
        "output_variable": output_var,
        "pre_trial_steps": pre_trial_steps,
        "per_trial_steps": per_trial_steps,
    }


def infer_expression_type(expression_dict, defined_vars, used_vars, line_num, current_result_var):
    expr_type = expression_dict.get("type")
    if expr_type == "literal_assignment":
        value = expression_dict.get("value")
        if isinstance(value, (int, float)):
            return "scalar"
        if isinstance(value, list):
            return "vector"
        if isinstance(value, _StringLiteral):
            return "string"
        raise ValuaScriptError(f"L{line_num}: Invalid or missing value assigned to '{current_result_var}'.")

    if expr_type == "execution_assignment":
        func_name = expression_dict["function"]
        args = expression_dict.get("args", [])

        if func_name not in FUNCTION_SIGNATURES:
            raise ValuaScriptError(f"L{line_num}: Unknown function '{func_name}'.")

        signature = FUNCTION_SIGNATURES[func_name]
        if not signature.get("variadic", False) and len(args) != len(signature["arg_types"]):
            raise ValuaScriptError(f"L{line_num}: Function '{func_name}' expects {len(signature['arg_types'])} argument{'s' if len(signature['arg_types']) != 1 else ''}, but got {len(args)}.")

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
                arg_type = infer_expression_type(temp_dict, defined_vars, used_vars, line_num, current_result_var)
            inferred_arg_types.append(arg_type)

        if signature.get("variadic"):
            if expected_types := signature["arg_types"]:
                for i, arg_type in enumerate(inferred_arg_types):
                    if arg_type != expected_types[0] and expected_types[0] != "any":
                        raise ValuaScriptError(f"L{line_num}: Argument {i+1} for function '{func_name}' expects a '{expected_types[0]}', but got a '{arg_type}'.")
        else:
            for i, expected_type in enumerate(signature["arg_types"]):
                if expected_type != "any" and expected_type != inferred_arg_types[i]:
                    raise ValuaScriptError(f"L{line_num}: Argument {i+1} for function '{func_name}' expects a '{expected_type}', but got a '{inferred_arg_types[i]}'.")

        return_type_rule = signature["return_type"]
        return return_type_rule(inferred_arg_types) if callable(return_type_rule) else return_type_rule
    raise ValuaScriptError(f"L{line_num}: Could not determine the type for '{current_result_var}'.")
