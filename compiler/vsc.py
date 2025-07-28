#!/usr/bin/env python3

import json
import argparse
import sys
import os
from lark import Lark, Transformer
from lark.exceptions import UnexpectedInput
from lark.lexer import Token


# ANSI Color Constants for terminal output ---
class TerminalColors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"


# --- Constants & Configuration ---
DIRECTIVE_CONFIG = {
    "iterations": {
        "required": True,
        "type": int,
        "error_missing": "The @iterations directive is mandatory (e.g., '@iterations = 10000').",
        "error_type": "The value for @iterations must be a whole number (e.g., 10000).",
    },
    "output": {
        "required": True,
        "type": str,
        "error_missing": "The @output directive is mandatory (e.g., '@output = final_result').",
        "error_type": "The value for @output must be a variable name (e.g., 'final_result').",
    },
}

FUNCTION_SIGNATURES = {
    "add": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar"},
    "subtract": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar"},
    "multiply": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar"},
    "divide": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar"},
    "power": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar"},
    "compose_vector": {"variadic": True, "arg_types": ["scalar"], "return_type": "vector"},
    "identity": {"variadic": False, "arg_types": ["any"], "return_type": lambda types: types[0] if types else "any"},
    "log": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    "log10": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    "exp": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    "sin": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    "cos": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    "tan": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    "sum_series": {"variadic": False, "arg_types": ["vector"], "return_type": "scalar"},
    "series_delta": {"variadic": False, "arg_types": ["vector"], "return_type": "vector"},
    "Bernoulli": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    "npv": {"variadic": False, "arg_types": ["scalar", "vector"], "return_type": "scalar"},
    "compound_series": {"variadic": False, "arg_types": ["scalar", "vector"], "return_type": "vector"},
    "get_element": {"variadic": False, "arg_types": ["vector", "scalar"], "return_type": "scalar"},
    "Normal": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar"},
    "Lognormal": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar"},
    "Beta": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar"},
    "Uniform": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar"},
    "grow_series": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "vector"},
    "interpolate_series": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "vector"},
    "capitalize_expense": {"variadic": False, "arg_types": ["scalar", "vector", "scalar"], "return_type": "vector"},
    "Pert": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "scalar"},
    "Triangular": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "scalar"},
}

OPERATOR_MAP = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide", "^": "power"}
TOKEN_FRIENDLY_NAMES = {
    "SIGNED_NUMBER": "a number",
    "CNAME": "a variable name",
    "expression": "a value or formula",
    "EQUAL": "an equals sign '='",
    "ADD": "a plus sign '+'",
    "SUB": "a minus sign '-'",
    "MUL": "a multiplication sign '*'",
    "DIV": "a division sign '/'",
    "POW": "a power sign '^'",
    "LPAR": "an opening parenthesis '('",
    "RPAR": "a closing parenthesis ')'",
    "LSQB": "an opening bracket '['",
    "RSQB": "a closing bracket ']'",
    "COMMA": "a comma ','",
    "AT": "an '@' symbol for a directive",
}


class ValuaScriptError(Exception):
    pass


class ValuaScriptTransformer(Transformer):
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
        if "." in val or "e" in val.lower():
            return float(val)
        return int(val)

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
        if isinstance(expression, dict):
            base_step.update({"type": "execution_assignment", **expression})
        elif isinstance(expression, Token):
            base_step.update({"type": "execution_assignment", "function": "identity", "args": [str(expression)]})
        else:
            base_step.update({"type": "literal_assignment", "value": expression})
        return base_step

    def start(self, children):
        directives = [item for item in children if isinstance(item, dict) and "name" in item]
        assignments = [item for item in children if isinstance(item, dict) and "result" in item]
        return {"directives": directives, "execution_steps": assignments}


def validate_recipe(recipe: dict):
    print("\n--- Running Semantic Validation ---")
    directives = {d["name"]: d for d in recipe.get("directives", [])}
    sim_config, output_var = {}, ""
    for name, config in DIRECTIVE_CONFIG.items():
        if config["required"] and name not in directives:
            raise ValuaScriptError(config["error_missing"])
        if name in directives:
            value = directives[name]["value"]
            if not isinstance(value, config["type"]):
                raise ValuaScriptError(f"L{directives[name]['line']}: {config['error_type']}")
            if name == "iterations":
                sim_config["num_trials"] = value
            elif name == "output":
                output_var = str(value)
    if not output_var:
        raise ValuaScriptError(DIRECTIVE_CONFIG["output"]["error_missing"])

    defined_vars = {}  # Stores var_name -> {'type': str, 'line': int}
    used_vars = set()  # Stores var_names that are used in expressions

    for step in recipe["execution_steps"]:
        line, result_var = step["line"], step["result"]
        if result_var in defined_vars:
            raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once.")
        if "args" in step:
            step["args"] = [str(arg) if isinstance(arg, Token) else arg for arg in step.get("args", [])]

        # Pass used_vars set to the inferencer
        rhs_type = infer_expression_type(step, defined_vars, used_vars, line, result_var)
        defined_vars[result_var] = {"type": rhs_type, "line": line}

    if output_var not in defined_vars:
        raise ValuaScriptError(f"The final @output variable '{output_var}' is not defined.")
    print(f"Found {len(defined_vars)} defined variables. Type inference successful.")

    # Unused Variable Check ---
    all_defined = set(defined_vars.keys())
    unused = all_defined - used_vars
    # The output variable is always considered "used" by the engine
    if output_var in unused:
        unused.remove(output_var)

    if unused:
        print(f"\n{TerminalColors.YELLOW}--- Compiler Warnings ---{TerminalColors.RESET}")
        for var in sorted(list(unused)):
            line_num = defined_vars[var]["line"]
            print(f"{TerminalColors.YELLOW}Warning: Variable '{var}' was defined on line {line_num} but was never used.{TerminalColors.RESET}")

    print(f"{TerminalColors.GREEN}--- Validation Successful ---{TerminalColors.RESET}")
    for step in recipe["execution_steps"]:
        if "value" in step and isinstance(step, Token):
            step["value"] = str(step["value"])
        if "line" in step:
            del step["line"]
    return {"simulation_config": sim_config, "execution_steps": recipe["execution_steps"], "output_variable": output_var}


# Function signature now accepts used_vars
def infer_expression_type(expression_dict, defined_vars, used_vars, line_num, current_result_var):
    expr_type = expression_dict.get("type")
    if expr_type == "literal_assignment":
        value = expression_dict.get("value")
        if isinstance(value, (int, float)):
            return "scalar"
        if isinstance(value, list):
            return "vector"
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
            if isinstance(arg, str):
                # Mark variable as used
                used_vars.add(arg)
                arg_type = defined_vars.get(arg, {}).get("type")
            else:
                temp_dict = {"type": "execution_assignment", **arg} if isinstance(arg, dict) else {"type": "literal_assignment", "value": arg}
                arg_type = infer_expression_type(temp_dict, defined_vars, used_vars, line_num, current_result_var)
            if arg_type is None:
                raise ValuaScriptError(f"L{line_num}: Variable '{arg}' used in function '{func_name}' is not defined.")
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


def format_lark_error(e: UnexpectedInput, script_content: str) -> str:
    line_content = script_content.splitlines()[e.line - 1].strip()
    if line_content.endswith("="):
        custom_msg = "Missing a value or formula after the equals sign '='."
        e.column = len(line_content) + 1
    elif line_content.startswith("let") and "=" not in line_content:
        custom_msg = "A variable definition must include an equals sign '=' and a value.\nExample: let my_variable = 100"
    elif "(" in line_content and ")" not in line_content:
        custom_msg = "It looks like you have an opening parenthesis '(' without a matching closing one ')'."
    elif "[" in line_content and "]" not in line_content:
        custom_msg = "It looks like you have an opening bracket '[' without a matching closing one ']'."
    else:
        custom_msg = f"The syntax is invalid here. I was expecting {', '.join(sorted([TOKEN_FRIENDLY_NAMES.get(s, s) for s in e.expected]))}."
    error_header = f"\n{TerminalColors.RED}--- SYNTAX ERROR ---{TerminalColors.RESET}"
    line_indicator = f"L{e.line} | {script_content.splitlines()[e.line - 1]}"
    pointer = f"{' ' * (e.column + 2 + len(str(e.line)))}^\n"
    error_message = f"{TerminalColors.RED}Error at line {e.line}: {custom_msg}{TerminalColors.RESET}"
    return f"{error_header}\n{line_indicator}\n{pointer}{error_message}"


def main():
    parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
    parser.add_argument("input_file", help="The path to the input .vs file.")
    parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file.")
    args = parser.parse_args()
    output_file_path = args.output_file or os.path.splitext(args.input_file)[0] + ".json"
    script_path = args.input_file
    print(f"--- Compiling {script_path} -> {output_file_path} ---")
    try:
        bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        grammar_path = os.path.join(bundle_dir, "valuascript.lark")
        with open(grammar_path, "r") as f:
            valuasc_grammar = f.read()
    except Exception as e:
        print(f"{TerminalColors.RED}FATAL ERROR: Could not load internal grammar file: {e}{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)
    lark_parser = Lark(valuasc_grammar, start="start", parser="lalr", transformer=ValuaScriptTransformer())
    try:
        with open(script_path, "r") as f:
            script_content = f.read()
        raw_recipe = lark_parser.parse(script_content)
        final_recipe = validate_recipe(raw_recipe)
        recipe_json = json.dumps(final_recipe, indent=2)
        with open(output_file_path, "w") as f:
            f.write(recipe_json)
    except UnexpectedInput as e:
        print(format_lark_error(e, script_content), file=sys.stderr)
        sys.exit(1)
    except ValuaScriptError as e:
        print(f"\n{TerminalColors.RED}--- SEMANTIC ERROR ---\n{e}{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"{TerminalColors.RED}ERROR: Script file '{script_path}' not found.{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n{TerminalColors.RED}--- UNEXPECTED COMPILER ERROR ---\n{type(e).__name__}: {e}{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)
    print(f"\n{TerminalColors.GREEN}--- Compilation Successful ---{TerminalColors.RESET}")
    print(f"Recipe written to {output_file_path}")


if __name__ == "__main__":
    main()
