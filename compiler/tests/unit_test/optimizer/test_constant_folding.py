import pytest
from pathlib import Path
from textwrap import dedent

from vsc.optimizer.ir_validator import IRValidator, IRValidationError

# --- Test Dependencies ---
from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.ir_generator import generate_ir
from vsc.optimizer.copy_propagation import run_copy_propagation
from vsc.optimizer.alias_resolver import run_alias_resolver
from .test_dead_code_elimination import run_full_pipeline_to_dce as run_full_pipeline
from vsc.optimizer.constant_folding import run_constant_folding

# --- Test Helpers ---


def create_dummy_file(directory, filename, content):
    """Helper to create files for the test pipeline."""
    script_content = dedent(content).strip()
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script_content)
    return str(path)


def run_full_pipeline_to_optimized_ir(script_content: str, file_path: str) -> list:
    """
    Runs the entire compiler front-end and all optimization phases in order,
    VALIDATING THE IR AT EACH STEP.
    """
    # 1. Frontend
    ast = parse_valuascript(dedent(script_content).strip())
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)

    # 2. IR Generation and Optimization Phases (with validation)
    initial_ir = generate_ir(validated_model)

    try:
        IRValidator(initial_ir).validate()

        post_copy_prop_ir = run_copy_propagation(initial_ir)
        IRValidator(post_copy_prop_ir).validate()

        post_alias_resolver_ir = run_alias_resolver(post_copy_prop_ir)
        IRValidator(post_alias_resolver_ir).validate()

        final_ir = run_constant_folding(post_alias_resolver_ir)
        IRValidator(final_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"An optimization phase produced an invalid IR: {e}")

    return final_ir


# --- 1. Basic Folding Tests ---


def test_folds_simple_literal_expression(tmp_path):
    """Tests that 'let x = 1 + 2' becomes 'let x = 3'."""
    script = """
    @iterations=1
    @output=x
    let x = 1 + 2 * 3
    """  # Expected: 1 + 6 = 7
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    assert optimized_ir[0] == {"type": "literal_assignment", "result": ["x"], "value": 7, "line": 3}


def test_propagation_and_folding(tmp_path):
    """Tests that a constant is first propagated, then folded."""
    script = """
    @iterations=1
    @output=y
    let x = 10
    let y = x * (3 + 2)
    """  # Expected: 10 * 5 = 50
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    assert optimized_ir[0]["type"] == "literal_assignment"  # let x = 10
    assert optimized_ir[1] == {"type": "literal_assignment", "result": ["y"], "value": 50, "line": 4}


# --- 2. Incomplete and No-Op Tests ---


def test_does_not_fold_stochastic_functions(tmp_path):
    """Ensures that calls to Normal, Uniform, etc., are never folded."""
    script = """
    @iterations=1
    @output=x
    let x = Normal(0, 1)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # Get the IR after identity elimination
    initial_ir = run_full_pipeline_to_optimized_ir(script, file_path)
    # Rerun just the constant folding pass to isolate its behavior
    final_ir = run_constant_folding(initial_ir)

    # The IR should be unchanged because Normal() is not constant
    assert initial_ir == final_ir
    assert final_ir[0]["function"] == "Normal"


def test_partially_folds_expressions(tmp_path):
    """Tests that an expression with both constant and variable parts is simplified."""
    script = """
    @iterations=1
    @output=y
    let x = Normal(0, 1)
    let y = x + (10 * 5)
    """  # Expected: x + 50
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    y_assignment = optimized_ir[1]
    assert y_assignment["type"] == "execution_assignment"
    assert y_assignment["function"] == "add"
    assert y_assignment["args"] == ["x", 50]


# --- 3. Conditional Folding ---


def test_folds_conditional_with_constant_true_condition(tmp_path):
    """If the condition is a literal 'true', the else branch is eliminated."""
    script = """
    @iterations=1
    @output=x
    let should_run = true
    let x = if should_run then 100 else 200
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    assert optimized_ir[1] == {"type": "literal_assignment", "result": ["x"], "value": 100, "line": 4}


def test_folds_conditional_with_constant_false_condition(tmp_path):
    """If the condition is a literal 'false', the then branch is eliminated."""
    script = """
    @iterations=1
    @output=x
    let x = if 1 > 2 then 100 else 200
    """  # 1 > 2 will be folded to false
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    assert optimized_ir[0] == {"type": "literal_assignment", "result": ["x"], "value": 200, "line": 3}


# --- 4. Integration Test ---


def test_full_pipeline_optimization_works_together(tmp_path):
    """
    A complex test to ensure copy prop, identity elim, and constant folding
    all work together correctly.
    """
    script = """
    @iterations=1
    @output=z
    func get_multiplier() -> scalar {
        return 2 * 5  # Should be folded to 10
    }
    func process(val: scalar) -> scalar {
        return val + get_multiplier()
    }
    let z = process(3)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    # Expected flow:
    # 1. IR Gen inlines everything with lots of identities.
    # 2. Copy Prop simplifies parameter passing.
    # 3. Identity Elim simplifies return statements.
    # 4. Constant Folding evaluates `2*5` to `10`, then `3+10` to `13`.

    assert len(optimized_ir) == 1
    assert optimized_ir[0] == {"type": "literal_assignment", "result": ["z"], "value": 13, "line": 9}


def test_folder_safely_skips_non_assignment_nodes(tmp_path):
    """
    This is a regression test that now also serves as a full integration test.
    It confirms that after Constant Folding creates dead code, the subsequent
    DCE pass successfully removes it.
    """
    script = """
    @iterations=1
    @output=z
    func my_func(p: scalar) -> scalar {
        let intermediate = p * 2 
        return intermediate + 5
    }
    let z = my_func(10)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # We now call the full pipeline helper which includes DCE.
    final_ir = run_full_pipeline(script, file_path)

    # The assertion now correctly expects DCE to have run.
    assert len(final_ir) == 1
    assert final_ir[0]["result"] == ["z"]
    assert final_ir[0]["value"] == 25


def test_nested_consitional_assignment(tmp_path):
    """
    This is a regression test that now also serves as a full integration test.
    """
    script = """
    @iterations = 10_000_000
    
    let is_active = true
    let market_is_open = false
    let initial_cost = 1_000
    let revenue_target = 1_200
    
    let target_was_met = revenue_target > initial_cost
    let costs_are_equal = initial_cost == 1000        
    
    
    let should_invest = target_was_met and not market_is_open
    
    let base_tax_rate = if is_active then 0.21 else 0.0
    
    let project_status_code = if target_was_met then 1 else 0
    
    let success_probability = 0.75
    let project_succeeds = Bernoulli(success_probability)
    
    let project_cash_flow = if project_succeeds == 1.0 then 500_000 else 20_000
    
    let bullish_forecast = [100, 120, 150]
    let bearish_forecast = [80, 85, 90]
    let cash_flow_scenario = if project_succeeds == 1.0 then bullish_forecast else bearish_forecast
    
    let asset_quality_rating = 85
    
    let risk_premium = if asset_quality_rating > 90 then 0.03
                       else if asset_quality_rating > 70 then 0.05
                       else 0.08
    
    func calculate_tax(income: scalar) -> scalar {
        \"\"\"Calculates tax with a simple two-tier bracket.\"\"\"
        let is_high_income = income > 100_000
        let is_medium_income = income > 70_000
        let tax_rate = if is_high_income then 0.40 else if is_medium_income then 0.3 else 0.2
        return income * tax_rate
    }
    
    let stochastic_income = project_cash_flow + Normal(5000, 2000)
    let tax_due = calculate_tax(stochastic_income)
    
    let a, b = CapitalizeExpenses(110, [100, 90, 80], 3)
    
    
    let income_after_tax = stochastic_income - tax_due + b
    
    let discount_rate = 0.08
    let final_project_value = income_after_tax / (1 + discount_rate) * (1 - risk_premium)
    
    @output = final_project_value
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # We now call the full pipeline helper which includes DCE.
    final_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert final_ir is not None
