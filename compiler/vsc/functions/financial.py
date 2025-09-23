"""
Signatures for quantitative finance functions.
"""

SIGNATURES = {
    "Npv": {
        "variadic": False,
        "arg_types": ["scalar", "vector"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the Net Present Value (Npv) of a series of cash flows.",
            "params": [{"name": "rate", "desc": "The discount rate per period."}, {"name": "cashflows", "desc": "A vector of cash flows."}],
            "returns": "The Npv as a scalar.",
        },
    },
    "CapitalizeExpenses": {
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
    "BlackScholes": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar", "scalar", "scalar", "string"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the price of a European option using the Black-Scholes model.",
            "params": [
                {"name": "spot", "desc": "The current spot price of the underlying asset."},
                {"name": "strike", "desc": "The strike price of the option."},
                {"name": "rate", "desc": "The annualized risk-free interest rate (e.g., 0.05 for 5%)."},
                {"name": "time_to_maturity", "desc": "The time to expiration in years."},
                {"name": "volatility", "desc": "The annualized volatility of the asset's returns (e.g., 0.2 for 20%)."},
                {"name": "option_type", "desc": "The type of option to price. Must be the string 'call' or 'put'."},
            ],
            "returns": "The theoretical price of the European option as a scalar.",
        },
    },
}
