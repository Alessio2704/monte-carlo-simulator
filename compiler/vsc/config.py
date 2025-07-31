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

# Each function is tagged with an execution_phase:
# - 'pre_trial': Executed once before the simulation trials begin. Ideal for loading data.
# - 'per_trial': Executed for every single simulation trial. This is for all calculations.
FUNCTION_SIGNATURES = {
    "add": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar", "execution_phase": "per_trial"},
    "subtract": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar", "execution_phase": "per_trial"},
    "multiply": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar", "execution_phase": "per_trial"},
    "divide": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar", "execution_phase": "per_trial"},
    "power": {"variadic": True, "arg_types": [], "return_type": lambda types: "vector" if "vector" in types else "scalar", "execution_phase": "per_trial"},
    "compose_vector": {"variadic": True, "arg_types": ["scalar"], "return_type": "vector", "execution_phase": "per_trial"},
    "identity": {"variadic": False, "arg_types": ["any"], "return_type": lambda types: types[0] if types else "any", "execution_phase": "per_trial"},
    "log": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "log10": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "exp": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "sin": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "cos": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "tan": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "sum_series": {"variadic": False, "arg_types": ["vector"], "return_type": "scalar", "execution_phase": "per_trial"},
    "series_delta": {"variadic": False, "arg_types": ["vector"], "return_type": "vector", "execution_phase": "per_trial"},
    "Bernoulli": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "npv": {"variadic": False, "arg_types": ["scalar", "vector"], "return_type": "scalar", "execution_phase": "per_trial"},
    "compound_series": {"variadic": False, "arg_types": ["scalar", "vector"], "return_type": "vector", "execution_phase": "per_trial"},
    "get_element": {"variadic": False, "arg_types": ["vector", "scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "delete_element": {"variadic": False, "arg_types": ["vector", "scalar"], "return_type": "vector", "execution_phase": "per_trial"},
    "Normal": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "Lognormal": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "Beta": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "Uniform": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "grow_series": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "vector", "execution_phase": "per_trial"},
    "interpolate_series": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "vector", "execution_phase": "per_trial"},
    "capitalize_expense": {"variadic": False, "arg_types": ["scalar", "vector", "scalar"], "return_type": "vector", "execution_phase": "per_trial"},
    "Pert": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "Triangular": {"variadic": False, "arg_types": ["scalar", "scalar", "scalar"], "return_type": "scalar", "execution_phase": "per_trial"},
    "read_csv_scalar": {"variadic": False, "arg_types": ["string", "string", "scalar"], "return_type": "scalar", "execution_phase": "pre_trial"},
    "read_csv_vector": {"variadic": False, "arg_types": ["string", "string"], "return_type": "vector", "execution_phase": "pre_trial"},
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
