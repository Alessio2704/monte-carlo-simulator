import json
from lark import Lark, Transformer, v_args

# Read the grammar file
with open("valuascript.lark", "r") as f:
    valuascript_grammar = f.read()


@v_args(inline=True)
class ValuaScriptTransformer(Transformer):
    """
    Transforms the ValuaScript parse tree into a Python dictionary.
    """

    # --- Methods for handling values ---
    def scalar_value(self, number):
        """Processes a single number."""
        return float(number)

    def vector(self, *items):
        """Processes a list of numbers from the vector rule."""
        return [float(i) for i in items]

    # --- Method for handling assignments ---
    def assignment(self, var_name, value):
        """
        Handles a generic assignment: 'let var = value'.
        The 'value' has already been processed by scalar_value or vector.
        """
        return (str(var_name), {"type": "fixed", "value": value})  # value is already a float or a list of floats

    # --- Methods for handling top-level blocks ---
    def iterations_setting(self, number):
        """Processes the '@iterations = 100000' directive."""
        return ("num_trials", int(number))

    def output_setting(self, var_name):
        """Processes the '@output = final_value' directive."""
        return ("output_variable", str(var_name))

    def start(self, *children):
        """
        Handles the top-level 'start' rule. It receives all processed
        child nodes as a flat list in 'children'.
        """
        # The 'children' list will contain:
        # [config_tuple, assignment_tuple_1, ..., assignment_tuple_n, output_tuple]

        config_tuple = children[0]
        output_tuple = children[-1]
        assignment_tuples = children[1:-1]

        recipe = {"simulation_config": {}, "inputs": {}, "operations": [], "output_variable": ""}

        # Populate the recipe from the processed blocks
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
    main("example_v2.valuascript")
