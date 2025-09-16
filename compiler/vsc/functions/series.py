"""
Signatures for vector and series manipulation functions.
"""

SIGNATURES = {
    "compose_vector": {
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
    "sum_series": {
        "variadic": False,
        "arg_types": ["vector"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the sum of all elements in a vector.", "params": [{"name": "vector", "desc": "The input vector."}], "returns": "The sum as a scalar."},
    },
    "series_delta": {
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
    "npv": {
        "variadic": False,
        "arg_types": ["scalar", "vector"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the Net Present Value (NPV) of a series of cash flows.",
            "params": [{"name": "rate", "desc": "The discount rate per period."}, {"name": "cashflows", "desc": "A vector of cash flows."}],
            "returns": "The NPV as a scalar.",
        },
    },
    "compound_series": {
        "variadic": False,
        "arg_types": ["scalar", "vector"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Projects a base value forward using a vector of period-specific growth rates.",
            "params": [{"name": "base_value", "desc": "The starting scalar value."}, {"name": "rates_vector", "desc": "A vector of growth rates for each period."}],
            "returns": "A new vector of compounded values.",
        },
    },
    "get_element": {
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
    "delete_element": {
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
    "grow_series": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Projects a series by applying a constant growth rate.",
            "params": [
                {"name": "base_value", "desc": "The starting scalar value."},
                {"name": "growth_rate", "desc": "The constant growth rate to apply each period (e.g., 0.05 for 5%)."},
                {"name": "periods", "desc": "The number of periods to project forward."},
            ],
            "returns": "A vector of projected values.",
        },
    },
    "interpolate_series": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Creates a vector by linearly interpolating between a start and end value.",
            "params": [
                {"name": "start_value", "desc": "The scalar value at the beginning of the series."},
                {"name": "end_value", "desc": "The scalar value at the end of the series."},
                {"name": "periods", "desc": "The total number of periods in the series."},
            ],
            "returns": "A new vector with the interpolated values.",
        },
    },
    "capitalize_expense": {
        "variadic": False,
        "arg_types": ["scalar", "vector", "scalar"],
        "return_type": ["scalar", "scalar"],
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the value of capitalized assets (e.g., R&D) and the amortization for the current year.",
            "params": [
                {"name": "current_expense", "desc": "The expense in the current period."},
                {"name": "past_expenses", "desc": "A vector of expenses from prior periods, oldest first."},
                {"name": "amortization_period", "desc": "The number of years over which the expense is amortized."},
            ],
            "returns": "The total capitalized asset value (scalar) and the amortization for the current year (scalar).",
        },
    },
}
