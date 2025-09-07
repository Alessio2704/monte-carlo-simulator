import pytest
from textwrap import dedent


@pytest.fixture
def create_manual_test_structure(tmp_path):
    """
    Creates the full, complex file structure from the manual test plan.
    This includes a diamond dependency import graph and files for testing
    circular import errors.
    """
    files = {
        "main.vs": """
            @import "modules/financials.vs"
            @import "modules/tax.vs"

            @iterations = 10_000
            @output = dcf_after_tax
            @output_file = "simulation_output.csv"

            # This function is defined locally in the main file.
            func get_cashflows() -> vector {
                \"\"\"Generates a simple two-year cash flow series.\"\"\"
                return [100, 110]
            }

            let initial_revenue = 1_000
            let asset_beta = 1.2
            let projected_rev = project_growth(initial_revenue)
            let dcf_value = calculate_dcf(get_cashflows(), asset_beta)
            let dcf_after_tax = apply_tax(dcf_value)
        """,
        "modules/financials.vs": """
            @module
            @import "core/metrics.vs"
            func project_growth(base: scalar) -> scalar {
                return base * (1 + Normal(0.10, 0.15))
            }
            func calculate_dcf(cashflows: vector, beta: scalar) -> scalar {
                let discount_rate = calculate_wacc(beta)
                return npv(discount_rate, cashflows)
            }
        """,
        "modules/tax.vs": """
            @module
            @import "core/utils.vs"
            func apply_tax(value: scalar) -> scalar {
                return value * (1 - 0.21)
            }
        """,
        "modules/core/metrics.vs": """
            @module
            @import "utils.vs"
            func calculate_wacc(beta: scalar) -> scalar {
                let equity_premium = 0.05
                let risk_free = get_risk_free_rate()
                return risk_free + beta * equity_premium
            }
        """,
        "modules/core/utils.vs": """
            @module
            func get_risk_free_rate() -> scalar {
                return 0.02
            }
        """,
        "cycle/cycle_a.vs": '@module\n@import "cycle_b.vs"',
        "cycle/cycle_b.vs": '@module\n@import "cycle_c.vs"',
        "cycle/cycle_c.vs": '@module\n@import "cycle_a.vs"',
    }

    for file_path, content in files.items():
        path = tmp_path / file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(content))

    return tmp_path
