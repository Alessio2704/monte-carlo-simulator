import pytest
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError


def test_comprehensive_boolean_and_conditional_logic():
    """
    This is an automated integration test that mirrors the manual test script.
    It validates that the compiler correctly handles a complex script involving
    booleans, all operators, if/else expressions, stochasticity, UDFs,
    and nested logic, with a specific focus on verifying the optimizer's
    partitioning of steps into pre-trial and per-trial phases.
    """

    script = """
    @iterations = 50_000
    @output = final_project_value

    # --- Phase 1: Basic Booleans and Comparisons ---
    let is_active = true
    let market_is_open = false
    let initial_cost = 1_000
    let revenue_target = 1_200
    let target_was_met = revenue_target > initial_cost
    let costs_are_equal = initial_cost == 1000

    # --- Phase 2: Logical Operators ---
    let should_invest = target_was_met and not market_is_open

    # --- Phase 3: The if/else Expression ---
    # 3a. Simple if/else with a literal
    let base_tax_rate = if is_active then 0.21 else 0.0

    # 3b. If/else with a calculated condition
    let project_status_code = if target_was_met then 1 else 0

    # 3c. If/else with a stochastic (per-trial) condition
    let success_probability = 0.75
    let project_succeeds = Bernoulli(success_probability)
    let project_cash_flow = if project_succeeds == 1.0 then 500_000 else 20_000

    # 3d. If/else returning vectors
    let bullish_forecast = [100, 120, 150]
    let bearish_forecast = [80, 85, 90]
    let cash_flow_scenario = if project_succeeds == 1.0 then bullish_forecast else bearish_forecast

    # --- Phase 4: Nested if/else ---
    let asset_quality_rating = 85
    let risk_premium = if asset_quality_rating > 90 then 0.03
                       else if asset_quality_rating > 70 then 0.05
                       else 0.08

    # --- Phase 5: User-Defined Function with Conditionals ---
    func calculate_tax(income: scalar) -> scalar {
        let is_high_income = income > 100_000
        let tax_rate = if is_high_income then 0.40 else 0.25
        return income * tax_rate
    }

    let stochastic_income = project_cash_flow + Normal(5000, 2000)
    let tax_due = calculate_tax(stochastic_income)
    let income_after_tax = stochastic_income - tax_due

    # --- Final Calculation ---
    let discount_rate = 0.08
    let final_project_value = income_after_tax / (1 + discount_rate)
    """

    recipe = compile_valuascript(script)
    assert recipe is not None, "Compilation failed unexpectedly"

    registry = recipe["variable_registry"]

    pre_trial_vars = {registry[index] for step in recipe["pre_trial_steps"] for index in (step["result"] if isinstance(step["result"], list) else [step["result"]])}

    per_trial_vars = {registry[index] for step in recipe["per_trial_steps"] for index in (step["result"] if isinstance(step["result"], list) else [step["result"]])}

    deterministic_vars = {
        "is_active",
        "market_is_open",
        "initial_cost",
        "revenue_target",
        "target_was_met",
        "costs_are_equal",
        "should_invest",
        "base_tax_rate",
        "project_status_code",
        "success_probability",
        "bullish_forecast",
        "bearish_forecast",
        "asset_quality_rating",
        "risk_premium",
        "discount_rate",
    }
    assert deterministic_vars.issubset(pre_trial_vars)

    assert "project_succeeds" in per_trial_vars

    assert "project_cash_flow" in per_trial_vars
    assert "cash_flow_scenario" in per_trial_vars

    assert "stochastic_income" in per_trial_vars

    assert "tax_due" in per_trial_vars

    assert "__calculate_tax_1__is_high_income" in per_trial_vars
    assert "__calculate_tax_1__tax_rate" in per_trial_vars

    assert "income_after_tax" in per_trial_vars
    assert "final_project_value" in per_trial_vars

    output_index = recipe["output_variable_index"]
    assert registry[output_index] == "final_project_value"


def test_deeply_nested_stochastic_conditional():
    """
    EDGE CASE TEST: Validates that stochasticity is correctly propagated
    out of a deeply nested if/else expression. This tests the optimizer's
    ability to traverse a complex AST.
    """
    script = """
    @iterations = 100
    @output = result
    let selector = 3
    let a = Normal(1,1) # Stochastic source
    let result = if selector == 1 then 10
                 else if selector == 2 then 20
                 else if selector == 3 then (
                    if selector > 2 then (
                        if selector * 1 == 3 then a  # Deepest branch is stochastic
                        else 40
                    ) else 50
                 ) else 60
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    registry = recipe["variable_registry"]

    per_trial_vars = {registry[index] for step in recipe["per_trial_steps"] for index in (step["result"] if isinstance(step["result"], list) else [step["result"]])}

    assert "a" in per_trial_vars

    assert "result" in per_trial_vars


def test_complex_logical_precedence():
    """
    EDGE CASE TEST: Ensures a complex chain of logical operators with mixed
    precedence is parsed and compiled correctly.
    (Precedence: NOT > AND > OR)
    """
    script = """
    @iterations = 1
    @output = result
    let a = false
    let b = true
    let c = false
    # This should evaluate as: false or (true and (not false)) -> false or (true and true) -> true
    let result = a or b and not c
    """

    recipe = compile_valuascript(script)
    assert recipe is not None

    registry = recipe["variable_registry"]
    pre_trial_vars = {registry[index] for step in recipe["pre_trial_steps"] for index in (step["result"] if isinstance(step["result"], list) else [step["result"]])}

    assert "result" in pre_trial_vars
