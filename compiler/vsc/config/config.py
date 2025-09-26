"""
Static configuration data for the ValuaScript compiler.
This includes directive rules, operator mappings, and token names.
Function signatures are now loaded dynamically from the 'vsc.functions' package.
"""

DIRECTIVE_CONFIG = {
    "iterations": {
        "required": lambda d: "module" not in d,  # Required only if not a module
        "value_type": int,
        "value_allowed": True,
        "allowed_in_module": False,
        "error_missing": "The @iterations directive is mandatory (e.g., '@iterations = 10000').",
        "error_type": "The value for @iterations must be a whole number (e.g., 10000).",
    },
    "output": {
        "required": lambda d: "module" not in d,  # Required only if not a module
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
        "value_allowed": False,  # This is a flag, not a setting
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
