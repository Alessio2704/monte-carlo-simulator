@iterations = 1000

# --- Inputs ---
let base_revenue = 100000.0
let growth_rate = Normal(0.08, 0.02)
let years = 5
let tax_rate = 0.21

# --- Operations (The Model Logic) ---
# 1. Project future revenue
let revenue_series = grow_series(base_revenue, growth_rate, years)

# 2. Calculate a simple pre-tax profit for the final year
let final_revenue = get_element(revenue_series, -1) # Get last element
let costs = multiply(final_revenue, 0.6) # Costs are 60% of revenue
let pre_tax_profit = subtract(final_revenue, costs)

# 3. Calculate net income using a nested expression
let net_income = multiply(pre_tax_profit, subtract(1, tax_rate))


# --- Model Output ---
@output = net_income