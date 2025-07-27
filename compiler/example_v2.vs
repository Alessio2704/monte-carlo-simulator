@iterations = 100000

# This is a regular comment that will be ignored.
# --- Model Inputs ---
let tax_rate = 0.21
let growth_rates = [0.1, 0.08, 0.05, 0.04] # A fixed vector of rates
let initial_investment = 50000.0

# --- Model Output ---
@output = final_value