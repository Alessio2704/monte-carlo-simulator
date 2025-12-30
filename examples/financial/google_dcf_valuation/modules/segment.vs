@module
@import "../assumptions/assumptions.vs"

func get_segment_data(market_share: scalar,
                        target_marget_share: scalar,
                        market_size: scalar,
                        market_cagr: scalar,
                        current_margin: scalar,
                        target_margin: scalar) -> (vector, vector) {
    """Computes the segment data: revenues and operating income for a segment based on its overall market of reference (TAM)"""

    let periods = get_periods()
    let market_total_revenues = grow_series(market_size, market_cagr, periods)
    let interim_market_share = interpolate_series(market_share, target_marget_share, periods)
    let revenues = market_total_revenues * interim_market_share
    let margins_interim = interpolate_series(current_margin, target_margin, periods)
    let operating_income = revenues * margins_interim   

    return (revenues, operating_income)

}

func get_base_segment_data(current_revenues: scalar,
                        segment_cagr: scalar,
                        current_margin: scalar,
                        target_margin: scalar) -> (vector, vector)  {
    """
    Computes the segment data: revenues and operating income for a segment where the segment represents the majority on its overall market of reference (TAM).

    In other words when it makes little sense to try to model the overall market because the segment is niche or because it is a very well known and established product (e.g. YouTube)
    """

    let periods = get_periods()
    let revenues = grow_series(current_revenues, segment_cagr, periods)
    let margins_interim = interpolate_series(current_margin, target_margin, periods)
    let operating_margin = revenues * margins_interim

    return (revenues, operating_margin)
}

func get_base_segment_data_from_cagr_vector(current_revenues: scalar,
                        segment_start_cagr: scalar,
                        segment_cagr_variation_per_period: scalar,
                        current_margin: scalar,
                        target_margin: scalar) -> (vector, vector)  {
    """
    Computes the segment data: revenues and operating income for a segment where the segment represents the majority on its overall market of reference (TAM).

    In other words when it makes little sense to try to model the overall market because the segment is niche or because it is a very well known and established product (e.g. YouTube).

    It calculates the revenues using the vector of rates for each compounding period instead of a single cagr value.
    """

    let periods = get_periods()
    let cagr_interim = grow_series(segment_start_cagr, segment_cagr_variation_per_period, periods)
    let revenues = compound_series(current_revenues, cagr_interim)
    let margins_interim = interpolate_series(current_margin, target_margin, periods)
    let operating_margin = revenues * margins_interim

    return (revenues, operating_margin)
}

func get_segment_reinvestment(current_sales_to_capital: scalar,
                            target_sales_to_capital: scalar,
                            revenues: vector,
                            ebit: vector,
                            total_revenues: vector) -> (vector, vector) {

    let sales_to_capital = interpolate_series(current_sales_to_capital, target_sales_to_capital, get_periods())
    let revenues_weight_percentage = revenues / total_revenues
    let ebit_margin_weight_percentage = ebit / revenues
    let ebit_dis = ebit_margin_weight_percentage * revenues_weight_percentage
    let reinvestment = series_delta(revenues) / sales_to_capital[:-1]

    return (reinvestment, ebit_dis)
}