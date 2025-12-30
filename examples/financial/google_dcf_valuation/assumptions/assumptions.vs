@module

# -- Valuation Specific

func get_periods() -> scalar {
    return 10
}

func get_rf() -> scalar {
    return 0.0436
}

func get_erp() -> scalar {
    return 0.0396
}

# -- Company Specific --

func get_beta() -> scalar {
    return 1.05
}

func get_bond_spread() -> scalar {
    return 0.0074
}

func get_marginal_tax() -> scalar {
    return 0.21
}

func get_effective_tax() -> scalar {
    return 0.17
}

func get_tax_rates_progression() -> vector {
    return interpolate_series(get_effective_tax(), get_marginal_tax(), get_periods())
}

func get_share_price() -> scalar {
    return 192.62
}

func get_shares_outstanding() -> scalar {
    return 5_817 + 847 + 5_430
}

func get_rd() -> (scalar, scalar) {
    let amortization_period = 3
    let current_expense = 27_364 + 49_326 - 23_763
    let past_expenses = [49_326, 45_427, 39_500]

    let capitalized_assets, amortization_current_year = capitalize_expense(current_expense, past_expenses, amortization_period)

    return (capitalized_assets, amortization_current_year)
}

func get_book_value_of_equity() -> scalar {
    return 362_916
}

func get_book_value_of_debt() -> scalar {
    return 23_607 + 11_952
}

func get_cash_and_marketable_securities() -> scalar {
    return 21_036 + 74_112
}

func get_return_on_capital_in_perpetuity() -> scalar {
    return 0.20
}