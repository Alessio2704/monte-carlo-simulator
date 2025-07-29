"""
Static configuration data for the ValuaScript compiler.
This includes directive rules, function signatures, and operator mappings.
"""

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
    "output_file": {"required": False, "type": str, "error_type": 'The value for @output_file must be a string literal (e.g., "path/to/results.csv").'},
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
    "STRING": "a string in double quotes",
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
