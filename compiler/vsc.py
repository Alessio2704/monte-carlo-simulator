#!/usr/bin/env python3

import json
import argparse
import sys
import os
from lark import Lark, Transformer
from lark.lexer import Token

# --- Constants ---
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

OPERATOR_MAP = {
    "+": "add",
    "-": "subtract",
    "*": "multiply",
    "/": "divide",
    "^": "power",
}


class ValuaScriptTransformer(Transformer):
    """
    Transforms the Lark parse tree into a structured JSON recipe,
    correctly handling and flattening infix operator chains.
    """

    # --- NEW, SMARTER INFIX HANDLER ---
    def infix_expression(self, items):
        if len(items) == 1:
            return items[0]

        # Start with the first operand
        tree = items[0]
        i = 1
        # Iterate through the remaining [operator, operand] pairs
        while i < len(items):
            op = items[i]
            right = items[i + 1]
            func_name = OPERATOR_MAP[op.value]

            # FLATTENING LOGIC: If the current tree is already a call to the same function,
            # and that function is associative (add/multiply), just append the new argument.
            if isinstance(tree, dict) and tree.get("function") == func_name and func_name in ("add", "multiply"):
                tree["args"].append(right)
            else:
                # Otherwise, create a new tree with the old tree as the left operand.
                tree = {"function": func_name, "args": [tree, right]}
            i += 2
        return tree

    # --- Pass-through methods for grammar hierarchy ---
    def expression(self, items):
        return items[0]

    def term(self, items):
        return items[0]

    def power(self, items):
        return items[0]

    def atom(self, items):
        return items[0]

    def arg(self, items):
        return items[0]

    # --- Token and Rule Transformers ---
    def SIGNED_NUMBER(self, n: Token) -> float:
        return float(n.value)

    def CNAME(self, c: Token) -> str:
        return str(c.value)

    def function_call(self, items):
        func_name, *args = items
        return {"function": func_name, "args": args}

    def vector(self, items):
        """Processes a list of numbers from the vector rule."""
        return [item for item in items if item is not None]

    def assignment(self, items):
        var_name, expression = items
        if isinstance(expression, dict):
            return {"type": "execution_assignment", "result": var_name, **expression}
        elif isinstance(expression, str):
            return {"type": "execution_assignment", "result": var_name, "function": "identity", "args": [expression]}
        else:
            return {"type": "literal_assignment", "result": var_name, "value": expression}

    def iterations_setting(self, items):
        return ("num_trials", int(items[0]))

    def output_setting(self, items):
        return ("output_variable", items[0])

    def start(self, children):
        config = children[0]
        output = children[-1]
        steps = children[1:-1]
        return {"simulation_config": {config[0]: config[1]}, "execution_steps": list(steps), "output_variable": output[1]}


# --- Semantic Validation ---
def validate_recipe(recipe: dict):
    print("\n--- Running Semantic Validation ---")
    defined_vars = set()
    for step in recipe["execution_steps"]:
        if step["type"] == "execution_assignment":
            func_name = step["function"]
            if func_name not in VALID_FUNCTIONS:
                raise ValueError(f"Unknown function '{func_name}' in assignment for '{step['result']}'.")

            def check_args(args_list, current_result_var):
                for arg in args_list:
                    if isinstance(arg, str) and arg not in defined_vars:
                        raise ValueError(f"Variable '{arg}' used in the calculation for '{current_result_var}' is not defined before its use.")
                    if isinstance(arg, dict):
                        nested_func = arg["function"]
                        if nested_func not in VALID_FUNCTIONS:
                            raise ValueError(f"Unknown nested function '{nested_func}'.")
                        check_args(arg["args"], current_result_var)

            check_args(step["args"], step["result"])
        result_var = step["result"]
        if result_var in defined_vars:
            raise ValueError(f"Variable '{result_var}' is defined more than once.")
        defined_vars.add(result_var)
    print(f"Found defined variables: {sorted(list(defined_vars))}")
    output_var = recipe["output_variable"]
    if not output_var:
        raise ValueError("An @output variable must be specified.")
    if output_var not in defined_vars:
        raise ValueError(f"The output variable '{output_var}' is not defined.")
    print(f"Output variable '{output_var}' is valid.")
    print("--- Validation Successful ---")


# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
    parser.add_argument("input_file", help="The path to the input .vs file.")
    parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file.")
    args = parser.parse_args()

    output_file_path = args.output_file or os.path.splitext(args.input_file)[0] + ".json"
    script_path = args.input_file
    print(f"--- Compiling {script_path} -> {output_file_path} ---")

    try:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            bundle_dir = sys._MEIPASS
        else:
            bundle_dir = os.path.dirname(os.path.abspath(__file__))
        grammar_path = os.path.join(bundle_dir, "valuascript.lark")
        with open(grammar_path, "r") as f:
            valuascript_grammar = f.read()
    except Exception as e:
        print(f"FATAL ERROR: Could not load internal grammar file: {e}", file=sys.stderr)
        sys.exit(1)

    lark_parser = Lark(valuascript_grammar, start="start", parser="lalr")

    try:
        with open(script_path, "r") as f:
            script_content = f.read()
    except FileNotFoundError:
        print(f"ERROR: Script file '{script_path}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        parse_tree = lark_parser.parse(script_content)
        transformer = ValuaScriptTransformer()
        recipe_dict = transformer.transform(parse_tree)
        validate_recipe(recipe_dict)
    except Exception as e:
        print(f"\n--- COMPILATION FAILED ---\n{e}", file=sys.stderr)
        sys.exit(1)

    recipe_json = json.dumps(recipe_dict, indent=2)
    try:
        with open(output_file_path, "w") as f:
            f.write(recipe_json)
    except IOError as e:
        print(f"ERROR: Could not write to output file '{output_file_path}': {e}", file=sys.stderr)
        sys.exit(1)

    print("\n--- Compilation Successful ---")
    print(f"Recipe written to {output_file_path}")


if __name__ == "__main__":
    main()
