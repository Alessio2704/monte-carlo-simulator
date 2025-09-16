"""
Signatures for scientific and simulation models.
"""

SIGNATURES = {
    "SirModel": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar", "scalar", "scalar", "scalar", "scalar"],
        "return_type": ["vector", "vector", "vector"],
        "is_stochastic": False,
        "doc": {
            "summary": "Runs a Susceptible-Infected-Recovered (SIR) epidemiological model.",
            "params": [
                {"name": "s0", "desc": "The initial number of susceptible individuals."},
                {"name": "i0", "desc": "The initial number of infected individuals."},
                {"name": "r0", "desc": "The initial number of recovered individuals."},
                {"name": "beta", "desc": "The average transmission rate."},
                {"name": "gamma", "desc": "The recovery rate (1 / duration of infection)."},
                {"name": "periods", "desc": "The number of time periods to simulate."},
                {"name": "dt", "desc": "The fraction of a time period per step (e.g., 1.0 for a full day)."},
            ],
            "returns": "A tuple of three vectors: (susceptible, infected, recovered) over time.",
        },
    },
}
