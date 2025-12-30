@module
@import "../assumptions/assumptions.vs"
@import "wacc.vs"

func get_sum_of_fcff(ebit_after_tax: vector,
                reinvestment_year_10: scalar,
                wacc: scalar,
                total_reinvestment: vector) -> scalar {

    let d_fcff_10 = (ebit_after_tax[-1] - reinvestment_year_10) / (1 + wacc)^10

    let d_fcff_to_9 = npv(wacc, (ebit_after_tax[:-1] - total_reinvestment))

    let sum_of_d_fcff = d_fcff_to_9 + d_fcff_10

    return sum_of_d_fcff
}

func get_discounted_terminal_value(total_revenues: vector,
                                total_ebit_dis: vector,
                                future_tax_rate: vector,
                                wacc: scalar
                                ) -> scalar {

    let rf = get_rf()

    let final_revenues = total_revenues[-1] * (1 + rf)
    let final_nopat = final_revenues * total_ebit_dis[-1] * (1 - future_tax_rate[-1])
    let final_reinvestment = rf / get_return_on_capital_in_perpetuity() * final_nopat

    let terminal_fcff = final_nopat - final_reinvestment
    let tv = terminal_fcff / (wacc - rf)
    let d_tv = tv / (1 + wacc)^get_periods()
    return d_tv
}