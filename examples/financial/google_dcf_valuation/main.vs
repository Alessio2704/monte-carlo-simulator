# -- Alphabet (Google) Valuation August 2025 --

@import "modules/wacc.vs"
@import "modules/segment.vs"
@import "modules/fcff.vs"

@iterations = 10_000_000

# -- R&D Capitalization
let value_of_research_assets, current_year_amortization = get_rd()

# -- WACC --
let wacc = get_wacc()

# -- Revenues study --

# -- GCP Assumptions --
let gcp_market_share = 0.11
let gcp_target_market_share = Uniform(0.1, 0.15)
let cloud_market_size = 13624 / gcp_market_share * 4
let cloud_cagr = Pert(0.15, 0.20, 0.25)
let gcp_current_margin = 0.15
let gcp_target_margin = Uniform(0.30, 0.40)

# -- GCP computation
let gcp_revenues, gcp_ebit = get_segment_data(gcp_market_share, gcp_target_market_share, cloud_market_size, cloud_cagr, gcp_current_margin, gcp_target_margin)



# -- YouTube Assumptions --
let yt_current_revenues = 9_796 * 4
let yt_cagr = 0.11
let yt_current_margin = 0.4
let yt_target_margin = Uniform(0.40, 0.45)

# -- YouTube computation
let yt_revenues, yt_ebit = get_base_segment_data(yt_current_revenues, yt_cagr, yt_current_margin, yt_target_margin)



# -- Google Network Assumptions --
let google_network_current_revenues = 7_354 * 4
let google_network_cagr = -0.10
let google_network_current_margin = 0.4
let google_network_target_margin = 0.4

# -- Google Network computation
let google_network_revenues, google_network_ebit = get_base_segment_data(google_network_current_revenues, google_network_cagr, google_network_current_margin, google_network_target_margin)



# -- Google Subscriptions Assumptions --
let google_subscriptions_current_revenues = 11_203 * 4
let google_subscriptions_cagr = 0.10
let google_subscriptions_current_margin = 0.2
let google_subscriptions_target_margin = Uniform(0.20, 0.25)

# -- Google Subscriptions computation
let google_subscriptions_revenues, google_subscriptions_ebit = get_base_segment_data(google_subscriptions_current_revenues, google_subscriptions_cagr, google_subscriptions_current_margin, google_subscriptions_target_margin)



# -- Google Search Assumptions --
let google_search_current_revenues = 54_190 * 4
let google_search_cagr = 0.10
let google_search_variation_per_period = -0.15
let google_search_current_margin = 0.3
let google_search_target_margin = Uniform(0.3, 0.4)

# -- Google Search computation
let google_search_revenues, google_search_ebit = get_base_segment_data_from_cagr_vector(google_search_current_revenues, google_search_cagr, google_search_variation_per_period, google_search_current_margin, google_search_target_margin)



# -- Total Revenues (sum of segments revenues) --
let total_revenues = gcp_revenues + yt_revenues + google_network_revenues + google_subscriptions_revenues + google_search_revenues
let total_ebit = gcp_ebit + yt_ebit + google_network_ebit + google_subscriptions_ebit + google_search_ebit



# -- NOPAT --
let future_tax_rate = get_tax_rates_progression()
let ebit_after_tax = total_ebit * (1 - future_tax_rate)


# -- Reinvestment (segments) --

# -- GCP --
let gcp_current_sales_to_capital = 0.22
let gcp_target_sales_to_capital = 1
let gcp_reinvestment, gcp_ebit_dis = get_segment_reinvestment(gcp_current_sales_to_capital, gcp_target_sales_to_capital, gcp_revenues, gcp_ebit, total_revenues)

# -- YouTube --
let yt_current_sales_to_capital = 1
let yt_target_sales_to_capital = 2
let yt_reinvestment, yt_ebit_dis = get_segment_reinvestment(yt_current_sales_to_capital, yt_target_sales_to_capital, yt_revenues, yt_ebit, total_revenues)

# -- Google Network --
let google_network_current_sales_to_capital = 2
let google_network_target_sales_to_capital = 2
let google_network_reinvestment, google_network_ebit_dis = get_segment_reinvestment(google_network_current_sales_to_capital, google_network_target_sales_to_capital, google_network_revenues, google_network_ebit, total_revenues)

# -- Google Subscriptions --
let google_subscriptions_current_sales_to_capital = 2
let google_subscriptions_target_sales_to_capital = 2
let google_subscriptions_reinvestment, google_subscriptions_ebit_dis = get_segment_reinvestment(google_subscriptions_current_sales_to_capital, google_subscriptions_target_sales_to_capital, google_subscriptions_revenues, google_subscriptions_ebit, total_revenues)

# -- Google Search --
let google_search_current_sales_to_capital = 2
let google_search_target_sales_to_capital = 2
let google_search_reinvestment, google_search_ebit_dis = get_segment_reinvestment(google_search_current_sales_to_capital, google_search_target_sales_to_capital, google_search_revenues, google_search_ebit, total_revenues)

# -- Reinvestment (total)
let total_reinvestment = gcp_reinvestment + yt_reinvestment + google_network_reinvestment + google_subscriptions_reinvestment + google_search_reinvestment
let total_current_capital = get_book_value_of_equity() + get_book_value_of_debt() - get_cash_and_marketable_securities() + value_of_research_assets
let capital_year_9 = total_current_capital + sum_series(total_reinvestment)

let year_10_growth = total_revenues[-1] / total_revenues[-2] - 1
let year_10_roi = total_ebit[-1] / capital_year_9
let reinvestment_year_10 = year_10_growth / year_10_roi * ebit_after_tax[-1]


# -- FCFF --
let sum_of_d_fcff = get_sum_of_fcff(ebit_after_tax, reinvestment_year_10, wacc, total_reinvestment)

# -- Terminal Value --
let total_ebit_dis = gcp_ebit_dis + yt_ebit_dis + google_network_ebit_dis + google_subscriptions_ebit_dis + google_search_ebit_dis
let d_tv = get_discounted_terminal_value(total_revenues, total_ebit_dis, future_tax_rate, wacc)

# -- Value of common equity --
let value_of_common_equity = sum_of_d_fcff + d_tv

# -- Adjustments --
let final_value_of_common_equity = value_of_common_equity - get_book_value_of_debt() + get_cash_and_marketable_securities()
let value_per_share = final_value_of_common_equity / get_shares_outstanding()

@output = value_per_share
@output_file = "results.csv"