"""
Signatures for vector and series manipulation functions.
"""

SIGNATURES = {
    "CompoundSerie": {
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
    "GrowSerie": {
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
    "InterpolateSerie": {
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
}
