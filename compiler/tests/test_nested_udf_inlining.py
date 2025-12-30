import pytest
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from tests.test_integration import find_engine_path, run_preview_integration


def test_udf_nested_in_simple_arithmetic():
    """
    BUG FIX TEST: Validates that a UDF called inside a simple
    arithmetic expression is correctly "lifted" and inlined.
    """
    script = """
    @iterations=1
    @output=result
    func get_five() -> scalar { return 5 }
    let base = 10
    let result = base + get_five()
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    registry = set(recipe["variable_registry"])
    assert "result" in registry
    assert any(v.startswith("__temp_") for v in registry)


def test_udf_deeply_nested_in_complex_expression():
    """
    BUG FIX TEST: Ensures the inliner can handle a UDF call
    that is several layers deep inside a complex expression with parentheses.
    """
    script = """
    @iterations=1
    @output=result
    func get_val() -> scalar { return 2 }
    let result = 100 / (10 - (4 * get_val())) # 100 / (10 - 8) = 50
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    registry = set(recipe["variable_registry"])
    assert "result" in registry
    assert any(v.startswith("__temp_") for v in registry)


def test_multiple_nested_udfs_in_one_expression():
    """
    BUG FIX TEST: Validates that multiple different nested UDFs in a single
    expression are all correctly lifted and inlined.
    """
    script = """
    @iterations=1
    @output=result
    func get_a() -> scalar { return 10 }
    func get_b() -> scalar { return 20 }
    let result = get_a() + get_b()
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    registry = set(recipe["variable_registry"])

    temp_vars = [v for v in registry if v.startswith("__temp_")]
    assert len(temp_vars) >= 2


def test_udf_nested_in_conditional_expression():
    """
    BUG FIX TEST: Ensures lifting works correctly for UDFs nested
    inside the 'then' or 'else' branch of a conditional expression.
    """
    script = """
    @iterations=1
    @output=result
    func get_true_val() -> scalar { return 100 }
    func get_false_val() -> scalar { return 200 }
    let selector = true
    let result = if selector then 5 + get_true_val() else 5 + get_false_val()
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    registry = set(recipe["variable_registry"])
    assert "result" in registry
    assert any(v.startswith("__temp_") for v in registry)


def test_end_to_end_reproducing_wacc_bug(find_engine_path):
    """
    END-TO-END VALIDATION: This test fully reproduces the user's bug report.
    It compiles the script with a UDF nested inside a complex calculation
    and verifies the final numerical result from the C++ engine, proving the
    entire toolchain is now correct.
    """
    script = """
    @iterations = 1
    @output = wacc

    # --- Assumptions ---
    func get_risk_free_rate() -> scalar { return 0.03 }
    func get_bond_spread() -> scalar { return 0.015 }
    func get_marginal_tax() -> scalar { return 0.25 }
    func get_beta() -> scalar { return 1.2 }
    func get_erp() -> scalar { return 0.05 }

    # --- Main WACC Calculation UDF ---
    func calculate_wacc() -> scalar {
        let equity_value = 1_500_000
        let debt_value = 500_000

        let risk_free = get_risk_free_rate()
        let spread = get_bond_spread()

        # THIS IS THE LINE THAT WAS CAUSING THE BUG
        # The call to get_marginal_tax() is nested inside the expression.
        let cost_of_debt = (risk_free + spread) * (1 - get_marginal_tax())

        let cost_of_equity = risk_free + (get_beta() * get_erp())

        let total_capital = equity_value + debt_value
        let equity_weight = equity_value / total_capital
        let debt_weight = debt_value / total_capital

        return (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt)
    }

    let wacc = calculate_wacc()
    """

    result = run_preview_integration(script, "wacc", find_engine_path)

    assert result.get("status") == "success"
    assert result.get("type") == "scalar"
    assert pytest.approx(result.get("value")) == 0.0759
