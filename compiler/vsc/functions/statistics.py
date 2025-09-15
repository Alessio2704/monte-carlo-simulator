"""
Signatures for statistical distribution (sampler) functions.
"""

SIGNATURES = {
    "Normal": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Normal (Gaussian) distribution.",
            "params": [{"name": "mean", "desc": "The mean (μ) of the distribution."}, {"name": "std_dev", "desc": "The standard deviation (σ) of the distribution."}],
            "returns": "A random scalar sample.",
        },
    },
    "Lognormal": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Lognormal distribution.",
            "params": [
                {"name": "log_mean", "desc": "The mean of the underlying normal distribution."},
                {"name": "log_std_dev", "desc": "The standard deviation of the underlying normal distribution."},
            ],
            "returns": "A random scalar sample.",
        },
    },
    "Beta": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Beta distribution.",
            "params": [{"name": "alpha", "desc": "The alpha (α) shape parameter."}, {"name": "beta", "desc": "The beta (β) shape parameter."}],
            "returns": "A random scalar sample between 0 and 1.",
        },
    },
    "Uniform": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Uniform distribution.",
            "params": [{"name": "min", "desc": "The minimum value of the range."}, {"name": "max", "desc": "The maximum value of the range."}],
            "returns": "A random scalar sample.",
        },
    },
    "Bernoulli": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Bernoulli distribution (a single coin flip).",
            "params": [{"name": "p", "desc": "The probability of success (returning 1.0)."}],
            "returns": "Either 1.0 (success) or 0.0 (failure).",
        },
    },
    "Pert": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a PERT (a modified Beta) distribution.",
            "params": [
                {"name": "min", "desc": "The minimum possible value."},
                {"name": "most_likely", "desc": "The most likely value (the mode)."},
                {"name": "max", "desc": "The maximum possible value."},
            ],
            "returns": "A random scalar sample.",
        },
    },
    "Triangular": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Triangular distribution.",
            "params": [
                {"name": "min", "desc": "The minimum possible value."},
                {"name": "most_likely", "desc": "The most likely value (the mode)."},
                {"name": "max", "desc": "The maximum possible value."},
            ],
            "returns": "A random scalar sample.",
        },
    },
}
