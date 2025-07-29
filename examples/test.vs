@iterations = 1000

let base_sales = 100
let growth = Pert(0.05, 0.10, 0.15)
let years = 10

let sales_forecast = grow_series(base_sales, growth, years)

let total_sales = sum_series(sales_forecast)

@output = total_sales
@output_file = "results.csv"
