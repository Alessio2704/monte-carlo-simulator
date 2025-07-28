#!/usr/bin/env python3

import json
import argparse
import sys
import os
from lark import Lark, Transformer
from lark.exceptions import UnexpectedInput
from lark.lexer import Token

# --- Constants & Configuration ---

# This dictionary drives the validation for all @-directives.
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

VALID_FUNCTIONS = {
    "add",
    "subtract",
    "multiply",
    "divide",
    "power",
    "log",
    "log10",
    "exp",
    "sin",
    "cos",
    "tan",
    "identity",
    "grow_series",
    "npv",
    "sum_series",
    "get_element",
    "series_delta",
    "compound_series",
    "compose_vector",
    "interpolate_series",
    "capitalize_expense",
    "Normal",
    "Pert",
    "Uniform",
    "Lognormal",
    "Triangular",
    "Bernoulli",
    "Beta",
}

OPERATOR_MAP = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide", "^": "power"}

# --- NEW: Expanded mapping for Lark tokens to friendly names ---
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


# --- Custom Exception for User-Friendly Errors ---
class ValuaScriptError(Exception):
    pass


# --- Transformer: From Parse Tree to Dictionary ---
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
        func_name_token, *args = items
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


# --- Semantic Validation ---
def validate_recipe(recipe: dict):
    print("\n--- Running Semantic Validation ---")
    directives = {d["name"]: d for d in recipe.get("directives", [])}
    sim_config = {}
    output_var = ""

    for name, config in DIRECTIVE_CONFIG.items():
        if config["required"] and name not in directives:
            raise ValuaScriptError(config["error_missing"])
        if name in directives:
            directive = directives[name]
            value = directive["value"]
            if not isinstance(value, config["type"]):
                raise ValuaScriptError(f"L{directive['line']}: {config['error_type']}")
            if name == "iterations":
                sim_config["num_trials"] = value
            elif name == "output":
                output_var = str(value)

    if not output_var:
        raise ValuaScriptError(DIRECTIVE_CONFIG["output"]["error_missing"])

    defined_vars = {}
    for step in recipe["execution_steps"]:
        line, result_var = step["line"], step["result"]
        if result_var in defined_vars:
            raise ValuaScriptError(f"L{line}: Variable '{result_var}' is defined more than once. It was first defined at L{defined_vars[result_var]}.")
        if "args" in step:
            step["args"] = [str(arg) if isinstance(arg, Token) else arg for arg in step.get("args", [])]
        if step["type"] == "execution_assignment":
            func_name = step["function"]
            if func_name not in VALID_FUNCTIONS:
                raise ValuaScriptError(f"L{line}: Unknown function '{func_name}' in assignment for '{result_var}'.")

            def check_args_recursively(args_list):
                for arg in args_list:
                    if isinstance(arg, str) and arg not in defined_vars:
                        raise ValuaScriptError(f"L{line}: Variable '{arg}' used in the calculation for '{result_var}' is not defined before this line.")
                    if isinstance(arg, dict):
                        nested_func = arg["function"]
                        if nested_func not in VALID_FUNCTIONS:
                            raise ValuaScriptError(f"L{line}: Unknown function '{nested_func}' used inside the expression for '{result_var}'.")
                        if "args" in arg:
                            arg["args"] = [str(a) if isinstance(a, Token) else a for a in arg.get("args", [])]
                        check_args_recursively(arg.get("args", []))

            check_args_recursively(step.get("args", []))
        defined_vars[result_var] = line

    if output_var not in defined_vars:
        raise ValuaScriptError(f"The final @output variable '{output_var}' is not defined anywhere in the script.")

    print(f"Found {len(defined_vars)} defined variables. Output variable '{output_var}' is valid.")
    print("--- Validation Successful ---")

    for step in recipe["execution_steps"]:
        if "value" in step and isinstance(step["value"], Token):
            step["value"] = str(step["value"])

    return {"simulation_config": sim_config, "execution_steps": recipe["execution_steps"], "output_variable": output_var}


# --- Main Execution ---
def format_lark_error(e: UnexpectedInput, script_content: str) -> str:
    """Creates a user-friendly error message from a Lark exception with contextual heuristics."""
    line_content = script_content.splitlines()[e.line - 1].strip()

    # --- HEURISTICS FOR COMMON ERRORS ---

    # Heuristic 1: Missing value after an equals sign.
    # This happens when the line ends with '='. Lark expects an 'expression'.
    if line_content.endswith("="):
        custom_msg = "Missing a value or formula after the equals sign '='."
        e.column = len(line_content) + 1  # Point to the end of the line

    # Heuristic 2: Missing equals sign in an assignment.
    # This happens when a `let` statement is followed by something other than '='.
    elif line_content.startswith("let") and "=" not in line_content:
        custom_msg = "A variable definition must include an equals sign '=' and a value.\nExample: let my_variable = 100"

    # Heuristic 3: Unmatched opening parenthesis or bracket.
    elif "(" in line_content and ")" not in line_content:
        custom_msg = "It looks like you have an opening parenthesis '(' without a matching closing one ')'."
    elif "[" in line_content and "]" not in line_content:
        custom_msg = "It looks like you have an opening bracket '[' without a matching closing one ']'."

    else:
        # Fallback to the generic message if no heuristic matches
        expected_str = ", ".join(sorted([TOKEN_FRIENDLY_NAMES.get(s, s) for s in e.expected]))
        custom_msg = f"The syntax is invalid here. I was expecting {expected_str}."

    # --- FORMAT THE FINAL OUTPUT ---
    error_header = "\n--- SYNTAX ERROR ---"
    line_indicator = f"L{e.line} | {script_content.splitlines()[e.line - 1]}"
    pointer = f"{' ' * (e.column + 2 + len(str(e.line)))}^\n"

    return f"{error_header}\n{line_indicator}\n{pointer}Error at line {e.line}: {custom_msg}"


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
            valuascript_grammar = f.read()
    except Exception as e:
        print(f"FATAL ERROR: Could not load internal grammar file: {e}", file=sys.stderr)
        sys.exit(1)

    lark_parser = Lark(valuascript_grammar, start="start", parser="lalr", transformer=ValuaScriptTransformer())

    try:
        with open(script_path, "r") as f:
            script_content = f.read()

        raw_recipe = lark_parser.parse(script_content)
        final_recipe = validate_recipe(raw_recipe)

        for step in final_recipe["execution_steps"]:
            del step["line"]

        recipe_json = json.dumps(final_recipe, indent=2)
        with open(output_file_path, "w") as f:
            f.write(recipe_json)

    except UnexpectedInput as e:
        error_msg = format_lark_error(e, script_content)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    except ValuaScriptError as e:
        print(f"\n--- SEMANTIC ERROR ---\n{e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: Script file '{script_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n--- UNEXPECTED COMPILER ERROR ---\n{e}", file=sys.stderr)
        sys.exit(1)

    print("\n--- Compilation Successful ---")
    print(f"Recipe written to {output_file_path}")


if __name__ == "__main__":
    main()
