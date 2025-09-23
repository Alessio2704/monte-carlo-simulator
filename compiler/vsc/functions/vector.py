"""
Signatures for vector manipulation functions.
"""

SIGNATURES = {
    "ComposeVector": {
        "variadic": True,
        "arg_types": ["any"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Creates a new vector from a series of values.",
            "params": [{"name": "value1, value2, ...", "desc": "The values to include in the vector. Input vectors will be flattened."}],
            "returns": "A new vector.",
        },
    },
    "SumVector": {
        "variadic": False,
        "arg_types": ["vector"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the sum of all elements in a vector.", "params": [{"name": "vector", "desc": "The input vector."}], "returns": "The sum as a scalar."},
    },
    "VectorDelta": {
        "variadic": False,
        "arg_types": ["vector"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the period-over-period change for a vector.",
            "params": [{"name": "vector", "desc": "The input vector."}],
            "returns": "A new vector of the differences, with one fewer element.",
        },
    },
    "GetElement": {
        "variadic": False,
        "arg_types": ["vector", "scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Retrieves an element from a vector at a specific index.",
            "params": [{"name": "vector", "desc": "The source vector."}, {"name": "index", "desc": "The zero-based index of the element. Negative indices count from the end."}],
            "returns": "The element at the specified index as a scalar.",
        },
    },
    "DeleteElement": {
        "variadic": False,
        "arg_types": ["vector", "scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Returns a new vector with the element at the specified index removed.",
            "params": [{"name": "vector", "desc": "The source vector."}, {"name": "index", "desc": "The zero-based index of the element to remove. Negative indices count from the end."}],
            "returns": "A new vector with the element removed.",
        },
    },
}
