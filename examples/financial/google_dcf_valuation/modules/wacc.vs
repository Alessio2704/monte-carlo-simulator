@module
@import "../assumptions/assumptions.vs"

func get_wacc() -> scalar {
    
    let shares_outstanding = get_shares_outstanding()
    let share_price = get_share_price()
    let equity_value = share_price * shares_outstanding

    let book_value_of_debt = get_book_value_of_debt()

    let beta = get_beta()

    let risk_free_rate = get_rf()

    let erp = get_erp()

    let k_equity = risk_free_rate + (beta * erp)

    let bond_spread = get_bond_spread()
    let k_debt = (risk_free_rate + bond_spread) * (1 - get_marginal_tax())

    let total_k = equity_value + book_value_of_debt
    let equity_percentage = equity_value / total_k
    let debt_percentage = 1 - equity_percentage

    let wacc = k_debt * debt_percentage + k_equity * equity_percentage

    return wacc
}