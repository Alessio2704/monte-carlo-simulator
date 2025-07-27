import json
from lark import Lark, Transformer, v_args
from lark.lexer import Token

# This dictionary maps the ValuaScript distribution names
# to the parameter names expected by the C++ engine.
DISTRIBUTION_PARAM_MAPPING = {
    # ValuaScript Name: [C++ Param Name 1, C++ Param Name 2, ...]
    "Normal": ["mean", "stddev"],
    "Pert": ["min", "mostLikely", "max"],
    "Uniform": ["min", "max"],
    "Lognormal": ["log_mean", "log_stddev"],
    "Triangular": ["min", "mostLikely", "max"],
    "Bernoulli": ["p"],
    "Beta": ["alpha", "beta"],
}

# This set contains all valid op_codes from the C++ engine.
# It is the "source of truth" for validating operations.
VALID_OPERATIONS = {
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
    "grow_series",
    "npv",
    "sum_series",
    "get_element",
    "series_delta",
    "compound_series",
    "compose_vector",
    "interpolate_series",
    "capitalize_expense",
}


@v_args(inline=True)
class ValuaScriptTransformer(Transformer):
    """
    Transforms the ValuaScript parse tree into a Python dictionary.
    """

    # --- Methods for literal values (expressions) ---
    def scalar_value(self, number):
        return float(number)

    def vector(self, *items):
        return [float(i) for i in items]

    def assignment(self, var_name, expression):
        """
        Handles all 'let' assignments. It intelligently determines if
        the assignment is an input or an operation.
        """
        # Case 1: The expression is a function call (e.g., Normal(...) or add(...))
        if isinstance(expression, dict):
            func_name = expression["op_code"]

            # Case 1a: The function is a DISTRIBUTION. This is an INPUT.
            if func_name in DISTRIBUTION_PARAM_MAPPING:
                args = expression["args"]
                param_names = DISTRIBUTION_PARAM_MAPPING[func_name]
                if len(args) != len(param_names):
                    raise ValueError(f"Distribution '{func_name}' wrong number of arguments.")

                params_dict = {name: float(arg) for name, arg in zip(param_names, args)}

                final_value = {"type": "distribution", "dist_name": func_name, "params": params_dict}
                return ("input", (str(var_name), final_value))

            # Case 1b: The function is a regular OPERATION.
            else:
                op_dict = expression
                op_dict["result"] = str(var_name)
                return ("operation", op_dict)

        # Case 2: The expression is a literal (scalar or vector). This is an INPUT.
        else:
            final_value = {"type": "fixed", "value": expression}
            return ("input", (str(var_name), final_value))

    # --- Methods for function calls and arguments ---
    def function_call(self, func_name, *args):
        """
        Processes ALL function calls into a generic dictionary.
        """
        processed_args = []
        for arg in args:
            if isinstance(arg, Token):
                if arg.type == "SIGNED_NUMBER":
                    processed_args.append(float(arg.value))
                else:  # CNAME
                    processed_args.append(str(arg.value))
            else:  # Nested function call (already a dict)
                processed_args.append(arg)

        return {"op_code": str(func_name), "args": processed_args}

    # --- Methods for top-level blocks ---
    def iterations_setting(self, number):
        return ("num_trials", int(number))

    def output_setting(self, var_name):
        return ("output_variable", str(var_name))

    def start(self, *children):
        config_tuple = children[0]
        output_tuple = children[-1]
        assignments = children[1:-1]

        recipe = {"simulation_config": {}, "inputs": {}, "operations": [], "output_variable": ""}

        recipe["simulation_config"][config_tuple[0]] = config_tuple[1]
        recipe["output_variable"] = output_tuple[1]

        for type, data in assignments:
            if type == "input":
                var_name, value_dict = data
                recipe["inputs"][var_name] = value_dict
            elif type == "operation":
                op_dict = data
                recipe["operations"].append(op_dict)

        return recipe


def validate_recipe(recipe: dict):
    """
    Performs semantic validation on the generated recipe dictionary.
    Raises a ValueError if any semantic errors are found.
    """
    print("\n--- Running Semantic Validation ---")

    # 1. Collect all variable names defined in the script.
    defined_vars = set(recipe["inputs"].keys())

    for op in recipe["operations"]:
        if op["result"] in defined_vars:
            raise ValueError(f"Variable '{op['result']}' is defined more than once.")
        defined_vars.add(op["result"])

    print(f"Found defined variables: {sorted(list(defined_vars))}")

    # 2. Check the output variable.
    output_var = recipe["output_variable"]
    if not output_var:
        raise ValueError("An @output variable must be specified.")
    if output_var not in defined_vars:
        raise ValueError(f"The output variable '{output_var}' is not defined in the script. " f"Available variables are: {sorted(list(defined_vars))}")
    print(f"Output variable '{output_var}' is valid.")

    # 3. Check all operations.
    for op in recipe["operations"]:
        op_code = op["op_code"]

        if op_code in DISTRIBUTION_PARAM_MAPPING:
            raise ValueError(f"Distribution function '{op_code}' cannot be used in a calculation. It can only be used to define an input.")

        if op_code not in VALID_OPERATIONS:
            raise ValueError(f"Unknown operation '{op_code}' in calculation for '{op['result']}'.")

        def check_args(args_list):
            for arg in args_list:
                if isinstance(arg, str) and arg not in defined_vars:
                    raise ValueError(f"Variable '{arg}' used in the calculation for '{op['result']}' " "is not defined.")
                if isinstance(arg, dict):
                    nested_op_code = arg["op_code"]
                    if nested_op_code in DISTRIBUTION_PARAM_MAPPING:
                        raise ValueError(f"Distribution function '{nested_op_code}' cannot be used in a calculation.")
                    if nested_op_code not in VALID_OPERATIONS:
                        raise ValueError(f"Unknown nested operation '{nested_op_code}'.")
                    check_args(arg["args"])

        check_args(op["args"])

    print("--- Validation Successful ---")


def main(script_path):
    """
    Main function to drive the transpilation.
    """
    print(f"--- Compiling {script_path} ---")

    try:
        with open("valuascript.lark", "r") as f:
            valuascript_grammar = f.read()
    except FileNotFoundError:
        print("ERROR: Grammar file 'valuascript.lark' not found.")
        return

    parser = Lark(valuascript_grammar, start="start", parser="lalr")

    try:
        with open(script_path, "r") as f:
            script_content = f.read()
    except FileNotFoundError:
        print(f"ERROR: Script file '{script_path}' not found.")
        return

    try:
        parse_tree = parser.parse(script_content)
    except Exception as e:
        print(f"--- PARSE ERROR ---\nCould not parse '{script_path}':\n{e}")
        return

    transformer = ValuaScriptTransformer()

    try:
        recipe_dict = transformer.transform(parse_tree)
    except ValueError as e:
        print(f"\n--- TRANSFORMATION ERROR ---\n{e}")
        return

    try:
        validate_recipe(recipe_dict)
    except ValueError as e:
        print(f"\n--- SEMANTIC ERROR ---\n{e}")
        return

    recipe_json = json.dumps(recipe_dict, indent=2)

    print("\n--- Generated JSON Recipe ---")
    print(recipe_json)


if __name__ == "__main__":
    main("example_v4.valuascript")
