@iterations = 100000

# --- Model Inputs ---
let tax_rate = 0.21
let growth_rates = [0.1, 0.08, 0.05, 0.04]

# New Distribution Inputs
let wacc = Pert(0.08, 0.09, 0.10)
let long_term_growth = Normal(0.025, 0.01)

# --- Model Output ---
@output = final_value