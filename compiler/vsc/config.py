"""
Static configuration data for the ValuaScript compiler.
This includes directive rules, operator mappings, and token names.
Function signatures are now loaded dynamically from the 'vsc.functions' package.
"""

DIRECTIVE_CONFIG = {
    "iterations": {
        "required": lambda d: "module" not in d,
        "value_type": int,
        "value_allowed": True,
        "allowed_in_module": False,
        "error_missing": "The @iterations directive is mandatory (e.g., '@iterations = 10000').",
        "error_type": "The value for @iterations must be a whole number (e.g., 10000).",
    },
    "output": {
        "required": lambda d: "module" not in d,
        "value_type": str,
        "value_allowed": True,
        "allowed_in_module": False,
        "error_missing": "The @output directive is mandatory (e.g., '@output = final_result').",
        "error_type": "The value for @output must be a variable name (e.g., 'final_result').",
    },
    "output_file": {
        "required": False,
        "value_type": str,
        "value_allowed": True,
        "allowed_in_module": False,
        "error_type": 'The value for @output_file must be a string literal (e.g., "path/to/results.csv").',
    },
    "module": {
        "required": False,
        "value_type": bool,
        "value_allowed": False,
        "allowed_in_module": True,
        "error_type": "The @module directive does not accept a value. It should be used as '@module'.",
    },
    "import": {
        "required": False,
        "value_type": str,
        "value_allowed": True,
        "allowed_in_module": True,
        "error_type": 'The @import directive expects a string literal path (e.g., @import "my_module.vs").',
    },
}

MATH_OPERATOR_MAP = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide", "^": "power"}
COMPARISON_OPERATOR_MAP = {
    "==": "__eq__",
    "!=": "__neq__",
    ">": "__gt__",
    "<": "__lt__",
    ">=": "__gte__",
    "<=": "__lte__",
}
LOGICAL_OPERATOR_MAP = {"and": "__and__", "or": "__or__"}


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
