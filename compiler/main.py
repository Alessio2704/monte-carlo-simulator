import json
from lark import Lark, Transformer, v_args

# Read the grammar file
with open("valuascript.lark", "r") as f:
    valuascript_grammar = f.read()


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


@v_args(inline=True)
class ValuaScriptTransformer(Transformer):
    """
    Transforms the ValuaScript parse tree into a Python dictionary.
    """

    # --- Methods for handling values ---
    def scalar_value(self, number):
        return float(number)

    def vector(self, *items):
        return [float(i) for i in items]

    # ==========================================================
    # --- NEW METHOD FOR DISTRIBUTIONS ---
    # ==========================================================
    def distribution(self, dist_name, *args):
        """Processes a distribution function call, e.g., Pert(0.08, 0.09, 0.10)"""
        dist_name_str = str(dist_name)

        # 1. Check if the distribution is known
        if dist_name_str not in DISTRIBUTION_PARAM_MAPPING:
            raise ValueError(f"Unknown distribution '{dist_name_str}'.")

        param_names = DISTRIBUTION_PARAM_MAPPING[dist_name_str]

        # 2. Check for the correct number of arguments
        if len(args) != len(param_names):
            raise ValueError(f"Distribution '{dist_name_str}' expected {len(param_names)} " f"arguments, but got {len(args)}.")

        # 3. Create the parameters dictionary
        params_dict = {name: float(arg) for name, arg in zip(param_names, args)}

        # 4. Return the complete structure for this input
        return {"type": "distribution", "dist_name": dist_name_str, "params": params_dict}

    # --- Method for handling assignments ---
    def assignment(self, var_name, value):
        """
        Handles a generic assignment: 'let var = value'.
        'value' is now either a float, a list, or a dictionary (from distribution).
        """
        # If the value is a distribution, it's already a complete dictionary.
        if isinstance(value, dict):
            # It already has the "type", "dist_name", etc. keys
            return (str(var_name), value)

        # Otherwise, it's a fixed scalar or vector.
        return (str(var_name), {"type": "fixed", "value": value})

    # --- Methods for handling top-level blocks ---
    def iterations_setting(self, number):
        return ("num_trials", int(number))

    def output_setting(self, var_name):
        return ("output_variable", str(var_name))

    def start(self, *children):
        config_tuple = children[0]
        output_tuple = children[-1]
        assignment_tuples = children[1:-1]

        recipe = {"simulation_config": {}, "inputs": {}, "operations": [], "output_variable": ""}

        recipe["simulation_config"][config_tuple[0]] = config_tuple[1]
        recipe["inputs"] = dict(assignment_tuples)
        recipe["output_variable"] = output_tuple[1]

        return recipe


def main(script_path):
    """
    Main function to drive the transpilation.
    Now takes the script_path as an argument.
    """
    parser = Lark(valuascript_grammar, start="start")

    with open(script_path, "r") as f:
        script_content = f.read()

    try:
        parse_tree = parser.parse(script_content)
    except Exception as e:
        print(f"Error parsing script '{script_path}':\n{e}")
        return

    transformer = ValuaScriptTransformer()
    recipe_dict = transformer.transform(parse_tree)
    recipe_json = json.dumps(recipe_dict, indent=2)

    print("--- Generated JSON Recipe ---")
    print(recipe_json)


if __name__ == "__main__":
    # We now pass the specific file to our main function.
    main("example_v3.valuascript")
