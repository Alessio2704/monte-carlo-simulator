#!/usr/bin/env python3

import json
import argparse
import sys
import os
from lark import Lark, Transformer, v_args
from lark.lexer import Token

# The set of all valid function names known to the C++ engine.
# This includes both operations and distribution samplers.
VALID_FUNCTIONS = {
    # Operations
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
    # Distribution Samplers
    "Normal",
    "Pert",
    "Uniform",
    "Lognormal",
    "Triangular",
    "Bernoulli",
    "Beta",
}


@v_args(inline=True)
class ValuaScriptTransformer(Transformer):
    """
    Transforms the ValuaScript parse tree into the new unified JSON format.
    """

    # --- Methods for literal values (expressions) ---
    def scalar_value(self, number):
        return float(number)

    def vector(self, *items):
        return [float(i) for i in items]

    def var_expression(self, var_name):
        """Transforms `let x = y` into an identity function call."""
        return {"function": "identity", "args": [str(var_name)]}

    def function_call(self, func_name, *args):
        """Processes a function call into a dictionary structure."""
        processed_args = []
        for arg in args:
            if isinstance(arg, Token):
                if arg.type == "SIGNED_NUMBER":
                    processed_args.append(float(arg.value))
                else:  # CNAME
                    processed_args.append(str(arg.value))
            else:  # Nested function call (dictionary)
                processed_args.append(arg)

        return {"function": str(func_name), "args": processed_args}

    # --- Method for the unified assignment rule ---
    def assignment(self, var_name, expression):
        """
        Handles all 'let' assignments and creates a step dictionary.
        """
        # Case 1: The expression is a function call (from function_call or var_expression)
        if isinstance(expression, dict):
            return {"type": "execution_assignment", "result": str(var_name), "function": expression["function"], "args": expression["args"]}
        # Case 2: The expression is a literal (float or list)
        else:
            return {"type": "literal_assignment", "result": str(var_name), "value": expression}

    # --- Methods for top-level blocks ---
    def iterations_setting(self, number):
        return ("num_trials", int(number))

    def output_setting(self, var_name):
        return ("output_variable", str(var_name))

    def start(self, *children):
        """
        Assembles the final recipe dictionary by manually unpacking children.
        """
        # The 'children' will be a list like:
        # [config_tuple, step_dict_1, step_dict_2, ..., output_tuple]
        config_tuple = children[0]
        output_tuple = children[-1]
        steps_list = list(children[1:-1])

        recipe = {"simulation_config": {}, "execution_steps": [], "output_variable": ""}
        recipe["simulation_config"][config_tuple[0]] = config_tuple[1]
        recipe["output_variable"] = output_tuple[1]
        recipe["execution_steps"] = steps_list

        return recipe


def validate_recipe(recipe: dict):
    """
    Performs semantic validation on the new unified recipe format.
    """
    print("\n--- Running Semantic Validation ---")

    defined_vars = set()

    # Iterate through steps to check for valid functions and defined variables
    for step in recipe["execution_steps"]:
        # Check all execution steps for valid functions and arguments
        if step["type"] == "execution_assignment":
            func_name = step["function"]
            if func_name not in VALID_FUNCTIONS:
                raise ValueError(f"Unknown function '{func_name}' in assignment for '{step['result']}'.")

            def check_args(args_list):
                for arg in args_list:
                    if isinstance(arg, str) and arg not in defined_vars:
                        raise ValueError(f"Variable '{arg}' used in the calculation for '{step['result']}' " "is not defined before its use.")
                    if isinstance(arg, dict):  # Nested execution
                        nested_func = arg["function"]
                        if nested_func not in VALID_FUNCTIONS:
                            raise ValueError(f"Unknown nested function '{nested_func}'.")
                        check_args(arg["args"])

            check_args(step["args"])

        # Add the variable defined in this step to the set for the next steps
        result_var = step["result"]
        if result_var in defined_vars:
            raise ValueError(f"Variable '{result_var}' is defined more than once.")
        defined_vars.add(result_var)

    print(f"Found defined variables: {sorted(list(defined_vars))}")

    # Check the output variable
    output_var = recipe["output_variable"]
    if not output_var:
        raise ValueError("An @output variable must be specified.")
    if output_var not in defined_vars:
        raise ValueError(f"The output variable '{output_var}' is not defined in the script. " f"Available variables are: {sorted(list(defined_vars))}")
    print(f"Output variable '{output_var}' is valid.")
    print("--- Validation Successful ---")


def main():
    """
    Main function to drive the transpilation (no changes from before).
    """
    parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
    parser.add_argument("input_file", help="The path to the input .vs file.")
    parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file. Defaults to the input filename with a .json extension.")
    args = parser.parse_args()

    if args.output_file:
        output_file_path = args.output_file
    else:
        base_name = os.path.splitext(args.input_file)[0]
        output_file_path = base_name + ".json"

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
