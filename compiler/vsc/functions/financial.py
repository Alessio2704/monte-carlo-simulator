"""
Signatures for quantitative finance functions.
"""

SIGNATURES = {
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
