"""
Signatures for core mathematical, logical, and comparison functions.
This now includes powerful `const_folder` lambdas that can handle
both scalar and vector arithmetic.
"""

import math


def _math_return_type(types: list) -> str:
    """Determines the return type for a math operation."""
    if "any" in types:
        return "any"
    return "vector" if "vector" in types else "scalar"


# --- Advanced Const Folder Lambdas ---


def _folder_for_elementwise_op(op):
    """
    A factory that creates a constant folding lambda for a given
    element-wise operation (e.g., add, sub, mul).
    It correctly handles scalar/vector broadcasting.
    """

    def folder(args):
        a, b = args[0], args[1]
        # Case 1: scalar op scalar
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return op(a, b)
        # Case 2: vector op vector
        if isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                return None  # Let semantic validator handle this error
            return [op(x, y) for x, y in zip(a, b)]
        # Case 3: vector op scalar (broadcasting)
        if isinstance(a, list) and isinstance(b, (int, float)):
            return [op(x, b) for x in a]
        # Case 4: scalar op vector (broadcasting)
        if isinstance(a, (int, float)) and isinstance(b, list):
            return [op(a, x) for x in b]
        return None  # Should not be reached with valid types

    return folder


def _variadic_folder_for_elementwise_op(op, initial_value):
    """
    A factory for variadic operations like add (+) and multiply (*).
    """

    def folder(args):
        # Check if there's a vector to determine the initial accumulator type
        has_vector = any(isinstance(arg, list) for arg in args)

        if not has_vector:
            # All scalars, simple case
            result = initial_value
            for arg in args:
                result = op(result, arg)
            return result
        else:
            # Vector math involved. Determine the length and promote scalars.
            vec_len = -1
            for arg in args:
                if isinstance(arg, list):
                    if vec_len == -1:
                        vec_len = len(arg)
                    elif vec_len != len(arg):
                        return None  # Mismatched vector lengths, cannot fold.

            # Promote all scalars to vectors of the correct length
            promoted_args = []
            for arg in args:
                if isinstance(arg, list):
                    promoted_args.append(arg)
                else:  # It's a scalar
                    promoted_args.append([arg] * vec_len)

            # Perform element-wise operation on all promoted arguments
            result_vector = list(promoted_args[0])
            for i in range(1, len(promoted_args)):
                for j in range(vec_len):
                    result_vector[j] = op(result_vector[j], promoted_args[i][j])
            return result_vector

    return folder


SIGNATURES = {
    # --- Internal Boolean & Comparison Operations ---
    "__eq__": {"variadic": False, "arg_types": ["any", "any"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: args[0] == args[1]},
    "__neq__": {"variadic": False, "arg_types": ["any", "any"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: args[0] != args[1]},
    "__gt__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: args[0] > args[1]},
    "__lt__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: args[0] < args[1]},
    "__gte__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: args[0] >= args[1]},
    "__lte__": {"variadic": False, "arg_types": ["scalar", "scalar"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: args[0] <= args[1]},
    "__and__": {"variadic": True, "arg_types": ["boolean"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: all(args)},
    "__or__": {"variadic": True, "arg_types": ["boolean"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: any(args)},
    "__not__": {"variadic": False, "arg_types": ["boolean"], "return_type": "boolean", "is_stochastic": False, "const_folder": lambda args: not args[0]},
    # --- Mathematical & Logical Operations ---
    "add": {"variadic": True, "arg_types": [], "return_type": _math_return_type, "is_stochastic": False, "const_folder": _variadic_folder_for_elementwise_op(lambda a, b: a + b, 0)},
    "subtract": {"variadic": False, "arg_types": ["any", "any"], "return_type": _math_return_type, "is_stochastic": False, "const_folder": _folder_for_elementwise_op(lambda a, b: a - b)},
    "multiply": {"variadic": True, "arg_types": [], "return_type": _math_return_type, "is_stochastic": False, "const_folder": _variadic_folder_for_elementwise_op(lambda a, b: a * b, 1)},
    "divide": {
        "variadic": False,
        "arg_types": ["any", "any"],
        "return_type": _math_return_type,
        "is_stochastic": False,
        "const_folder": _folder_for_elementwise_op(lambda a, b: a / b if b != 0 else None),
    },
    "power": {"variadic": False, "arg_types": ["any", "any"], "return_type": _math_return_type, "is_stochastic": False, "const_folder": _folder_for_elementwise_op(lambda a, b: a**b)},
    "identity": {
        "variadic": False,
        "arg_types": ["any"],
        "return_type": lambda types: types[0] if types else "any",
        "is_stochastic": False,
        "const_folder": None,
    },
    "log": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "is_stochastic": False, "const_folder": lambda args: math.log(args[0]) if args[0] > 0 else None},
    "log10": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "is_stochastic": False, "const_folder": lambda args: math.log10(args[0]) if args[0] > 0 else None},
    "exp": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar", "is_stochastic": False, "const_folder": lambda args: math.exp(args[0])},
}
