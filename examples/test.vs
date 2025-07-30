# This model demonstrates reading data from an external CSV file.

@iterations = 20000
@output = final_year_sales
@output_file = "csv_test_results.csv"

# --- Pre-Trial Data Loading ---
# Read a single value (scalar) from the CSV.
let base_sales = read_csv_scalar("test_assumptions.csv", "InitialSales", 0)

# Read an entire column (vector) from the CSV.
let growth_rates_forecast = read_csv_vector("test_assumptions.csv", "GrowthRate")


# --- Per-Trial Calculations ---
# Add some randomness to the base sales figure for our simulation.
let simulated_base_sales = Normal(base_sales, 50)

# Use the loaded growth rates to project sales forward.
let sales_projection = compound_series(simulated_base_sales, growth_rates_forecast)

# Get the sales figure from the final year of the projection.
let final_year_sales = get_element(sales_projection, -1)