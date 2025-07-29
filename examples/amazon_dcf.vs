# -----------------------------------------------------------------------------
# ValuaScript Model: Amazon Inc. (AMZN) Valuation (Infix Operator Style)
# Demonstrates the use of natural mathematical operators for calculations.
# All figures and assumptions are derived from the appendix, circa early 2024.
# -----------------------------------------------------------------------------

@iterations = 10000

# =============================================================================
# PART 1: WACC (DISCOUNT RATE) ESTIMATION
# =============================================================================

# --- 1.1: Cost of Equity Inputs ---
let rf_rate = 0.04663
let equity_risk_premium = 0.0476
let levered_beta = 1.08

# --- 1.2: Cost of Debt Inputs ---
let debt_spread = 0.0070

# --- 1.3: Capital Structure and Tax ---
let weight_equity = 0.92
let weight_debt = 0.08
let tax_rate = 0.25

# --- 1.4: WACC Calculation ---
let cost_of_equity = rf_rate + (levered_beta * equity_risk_premium)
let pretax_cost_of_debt = rf_rate + debt_spread
let after_tax_cost_of_debt = pretax_cost_of_debt * (1 - tax_rate)

let wacc = (cost_of_equity * weight_equity) + (after_tax_cost_of_debt * weight_debt)


# =============================================================================
# PART 2: FCFF (FREE CASH FLOW) ESTIMATION
# =============================================================================

# --- 2.1: Revenue Forecasts (10 years) ---
let base_rev_aws = 90.757
let base_rev_ads = 46.906
let base_rev_3ps = 140.053
let base_rev_subs = 40.209
let base_rev_online = 231.872
let base_rev_physical = 20.030
let base_rev_other = 4.958

let growth_aws = 0.15
let growth_ads = 0.06
let growth_3ps = Pert(0.09, 0.12, 0.15)
let growth_subs = Pert(0.05, 0.08, 0.12)
let growth_online = 0.03
let growth_physical = 0.03
let growth_other = 0.0

# Functions like grow_series are still used for complex operations
let rev_series_aws = grow_series(base_rev_aws, growth_aws, 10)
let rev_series_ads = grow_series(base_rev_ads, growth_ads, 10)
let rev_series_3ps = grow_series(base_rev_3ps, growth_3ps, 10)
let rev_series_subs = grow_series(base_rev_subs, growth_subs, 10)
let rev_series_online = grow_series(base_rev_online, growth_online, 10)
let rev_series_physical = grow_series(base_rev_physical, growth_physical, 10)
let rev_series_other = grow_series(base_rev_other, growth_other, 10)

# Aggregate total revenues with infix operators
let total_revenues = rev_series_aws + rev_series_ads + rev_series_3ps + rev_series_subs + rev_series_online + rev_series_physical + rev_series_other

# --- 2.2: Operating Margin & EBIT Forecast ---
let margin_aws = 0.30
let margin_ads = 0.50
let margin_3ps = 0.25
let margin_subs = Pert(0.15, 0.20, 0.30)
let margin_online = 0.06
let margin_physical = 0.05
let margin_other = 0.0

let ebit_series_aws = rev_series_aws * margin_aws
let ebit_series_ads = rev_series_ads * margin_ads
let ebit_series_3ps = rev_series_3ps * margin_3ps
let ebit_series_subs = rev_series_subs * margin_subs
let ebit_series_online = rev_series_online * margin_online
let ebit_series_physical = rev_series_physical * margin_physical
let ebit_series_other = rev_series_other * margin_other

let total_ebit = ebit_series_aws + ebit_series_ads + ebit_series_3ps + ebit_series_subs + ebit_series_online + ebit_series_physical + ebit_series_other
let nopat = total_ebit * (1 - tax_rate)

# --- 2.3: Reinvestment Forecast ---
let sales_to_capital_series = interpolate_series(1.27, 2.72, 10)
let revenue_change = series_delta(total_revenues)
let reinvestment = revenue_change / sales_to_capital_series

# --- 2.4: Final FCFF Calculation ---
let free_cash_flow_firm = nopat - reinvestment


# =============================================================================
# PART 3: TERMINAL VALUE AND FINAL VALUATION
# =============================================================================

# --- 3.1: Terminal Value Inputs ---
let terminal_growth_rate = rf_rate
let terminal_wacc = Pert(rf_rate + 0.045, rf_rate + 0.065, rf_rate + 0.075)

# --- 3.2: Terminal Value Calculation ---
let last_fcff = get_element(free_cash_flow_firm, -1)
let fcff_terminal_year = last_fcff * (1 + terminal_growth_rate)
let terminal_value_future = fcff_terminal_year / (terminal_wacc - terminal_growth_rate)

# --- 3.3: Discounting and Enterprise Value ---
let pv_of_fcff = npv(wacc, free_cash_flow_firm)
let discount_factor_tv = (1 + wacc) ^ 10
let pv_of_terminal_value = terminal_value_future / discount_factor_tv
let value_of_operating_assets = pv_of_fcff + pv_of_terminal_value

# --- 3.4: Valuation Adjustments ---
let debt_value = 162.0
let cash_value = 90.0

let value_of_equity = value_of_operating_assets + cash_value - debt_value
let shares_outstanding = 10.38
let value_per_share = value_of_equity / shares_outstanding

@output = value_per_share
@output_file = "results.csv"