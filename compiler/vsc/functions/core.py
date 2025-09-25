"""
Signatures for core mathematical, logical, and comparison functions.
"""


def _math_return_type(types: list) -> str:
    """Determines the return type for a math operation."""
    if "any" in types:
        return "any"
    return "vector" if "vector" in types else "scalar"


SIGNATURES = {
    # --- Internal Boolean & Comparison Operations (from operators) ---
    "__eq__": {"variadic": False, "arg_types": ["any", "any"], "return_type": "boolean", "is_stochastic": False},
    "__neq__": {"variadic": False, "arg_types": ["any", "any"], "return_type": "boolean", "is_stochastic": False},
    "__gt__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False},
    "__lt__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False},
    "__gte__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False},
    "__lte__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False},
    "__and__": {"variadic": True, "arg_types": ["boolean"], "return_type": "boolean", "is_stochastic": False},
    "__or__": {"variadic": True, "arg_types": ["boolean"], "return_type": "boolean", "is_stochastic": False},
    "__not__": {"variadic": False, "arg_types": ["boolean"], "return_type": "boolean", "is_stochastic": False},
    # --- Mathematical & Logical Operations ---
    "add": {
        "variadic": True,
        "arg_types": [],
        "return_type": _math_return_type,
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise addition on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "subtract": {
        "variadic": True,
        "arg_types": [],
        "return_type": _math_return_type,
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise subtraction on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "multiply": {
        "variadic": True,
        "arg_types": [],
        "return_type": _math_return_type,
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise multiplication on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "divide": {
        "variadic": True,
        "arg_types": [],
        "return_type": _math_return_type,
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise division on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "power": {
        "variadic": True,
        "arg_types": [],
        "return_type": _math_return_type,
        "is_stochastic": False,
        "doc": {
            "summary": "Raises the first argument to the power of the second.",
            "params": [{"name": "base", "desc": "The base value(s)."}, {"name": "exponent", "desc": "The exponent value(s)."}],
            "returns": "A scalar or vector result.",
        },
    },
    "identity": {
        "variadic": False,
        "arg_types": ["any"],
        "return_type": lambda types: types[0] if types else "any",
        "is_stochastic": False,
        "doc": {
            "summary": "Returns the input value unchanged. Useful for assigning a variable to another.",
            "params": [{"name": "value", "desc": "The value to return."}],
            "returns": "The original value.",
        },
    },
    "log": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the natural logarithm of a scalar.", "params": [{"name": "value", "desc": "The input scalar."}], "returns": "The natural logarithm as a scalar."},
    },
    "log10": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the base-10 logarithm of a scalar.", "params": [{"name": "value", "desc": "The input scalar."}], "returns": "The base-10 logarithm as a scalar."},
    },
    "exp": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the exponential (e^x) of a scalar.", "params": [{"name": "value", "desc": "The input scalar."}], "returns": "The exponential as a scalar."},
    },
}
