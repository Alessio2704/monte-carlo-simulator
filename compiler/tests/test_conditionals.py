import pytest
import sys
import os

# Make the compiler module available for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode

# --- 1. VALID CONDITIONAL EXPRESSIONS (IF/THEN/ELSE) ---


def test_if_then_else_with_boolean_literals():
    """Tests basic if/then/else functionality with true/false conditions."""
    script_true = "@iterations=1\n@output=x\nlet x = if true then 10 else 20"
    recipe_true = compile_valuascript(script_true)
    assert recipe_true is not None

    script_false = "@iterations=1\n@output=x\nlet x = if false then 10 else 20"
    recipe_false = compile_valuascript(script_false)
    assert recipe_false is not None


def test_if_then_else_with_comparison_condition():
    """Tests using a comparison operator in the 'if' condition."""
    script = """
    @iterations=1
    @output=result
    let a = 100
    let b = 50
    let result = if a > b then a else b
    """
    recipe = compile_valuascript(script)
    assert recipe is not None


def test_if_then_else_with_logical_condition():
    """Tests using a logical operator in the 'if' condition."""
    script = """
    @iterations=1
    @output=result
    let a = 10
    let b = 20
    let result = if (a > 5 and b < 30) then 1 else 0
    """
    recipe = compile_valuascript(script)
    assert recipe is not None


def test_if_then_else_returning_vectors():
    """Tests that if/then/else can correctly handle vector types in its branches."""
    script = """
    @iterations=1
    @output=result
    let condition = true
    let vec1 = [1, 2, 3]
    let vec2 = [4, 5, 6]
    let result = if condition then vec1 else vec2
    """
    recipe = compile_valuascript(script)
    assert recipe is not None


def test_nested_if_then_else():
    """Tests a conditional expression nested inside another."""
    script = """
    @iterations=1
    @output=result
    let a = 10
    let b = 20
    let result = if a > 5 then (if b < 10 then 1 else 2) else 3
    """
    recipe = compile_valuascript(script)
    assert recipe is not None


def test_if_then_else_inside_udf():
    """Ensures conditional logic is correctly parsed and validated inside a UDF."""
    script = """
    @iterations=1
    @output=result
    func max_val(a: scalar, b: scalar) -> scalar {
        return if a > b then a else b
    }
    let result = max_val(100, 200)
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    # Check that the inliner produced the mangled variables for the function parameters
    assert "__max_val_1__a" in recipe["variable_registry"]
    assert "__max_val_1__b" in recipe["variable_registry"]


# --- 2. VALID COMPARISON AND LOGICAL OPERATORS ---


@pytest.mark.parametrize(
    "op, a, b, expected_outcome",
    [
        (">", 10, 5, "a"),
        ("<", 10, 5, "b"),
        ("==", 10, 10, "a"),
        ("!=", 10, 5, "a"),
        (">=", 10, 10, "a"),
        ("<=", 10, 5, "b"),
    ],
)
def test_all_comparison_operators(op, a, b, expected_outcome):
    """A comprehensive test for all binary comparison operators."""
    script = f"""
    @iterations=1
    @output=result
    let a = {a}
    let b = {b}
    let choice = if a {op} b then a else b
    let result = choice
    """
    recipe = compile_valuascript(script)
    assert recipe is not None


@pytest.mark.parametrize(
    "expression, expected_outcome",
    [
        ("a > 5 and b < 15", "is_true"),
        ("a > 100 or b < 15", "is_true"),
        ("not (a > 100)", "is_true"),
        ("not (a > 5)", "is_false"),
        ("true and false", "is_false"),
        ("true or false", "is_true"),
    ],
)
def test_all_logical_operators(expression, expected_outcome):
    """A comprehensive test for all logical operators."""
    script = f"""
    @iterations=1
    @output=result
    let a = 10
    let b = 10
    let is_true = 1
    let is_false = 0
    let result = if {expression} then is_true else is_false
    """
    recipe = compile_valuascript(script)
    assert recipe is not None


# --- 3. ERROR HANDLING FOR INVALID CONDITIONAL LOGIC ---


@pytest.mark.parametrize(
    "script_body, expected_code",
    [
        pytest.param("let x = if 100 then 1 else 0", ErrorCode.IF_CONDITION_NOT_BOOLEAN, id="if_cond_not_bool"),
        pytest.param("let v = [1]\nlet x = if v then 1 else 0", ErrorCode.IF_CONDITION_NOT_BOOLEAN, id="if_cond_vector"),
        pytest.param("let x = if true then 10 else [1,2]", ErrorCode.IF_ELSE_TYPE_MISMATCH, id="if_else_mismatch"),
        pytest.param("let x = true and 1", ErrorCode.LOGICAL_OPERATOR_TYPE_MISMATCH, id="and_type_mismatch"),
        pytest.param("let x = 0 or false", ErrorCode.LOGICAL_OPERATOR_TYPE_MISMATCH, id="or_type_mismatch"),
        pytest.param("let x = not 10", ErrorCode.LOGICAL_OPERATOR_TYPE_MISMATCH, id="not_type_mismatch"),
        pytest.param("let x = [1] > 10", ErrorCode.ARGUMENT_TYPE_MISMATCH, id="gt_type_mismatch"),
        pytest.param("let x = 10 == [1]", ErrorCode.COMPARISON_TYPE_MISMATCH, id="eq_type_mismatch"),
    ],
)
def test_conditional_semantic_errors(script_body, expected_code):
    """Tests that the compiler catches common semantic errors in conditional logic."""
    script = f"@iterations=1\n@output=x\n{script_body}"
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == expected_code


# --- 4. INTEGRATION WITH OPTIMIZATIONS ---


def test_deterministic_if_is_moved_to_pre_trial():
    """
    Ensures that an if/else statement with deterministic inputs is correctly
    identified as loop-invariant and moved to the pre-trial phase.
    """
    script = """
    @iterations=100
    @output=result
    let a = 10
    let b = 20
    let result = if a > b then a else b
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    registry = recipe["variable_registry"]
    pre_trial_vars = {registry[step["result_index"]] for step in recipe["pre_trial_steps"]}
    per_trial_vars = {registry[step["result_index"]] for step in recipe["per_trial_steps"]}

    assert "result" in pre_trial_vars
    assert not per_trial_vars


def test_stochastic_if_branch_taints_result():
    """
    Tests that if one branch of a conditional is stochastic, the result variable
    is correctly marked as stochastic and remains in the per-trial phase.
    """
    script = """
    @iterations=100
    @output=result
    let a = 10
    let b_sto = Normal(20, 5)
    # The condition is deterministic, but a potential result is not.
    let result = if a > 0 then b_sto else a
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    registry = recipe["variable_registry"]
    pre_trial_vars = {registry[step["result_index"]] for step in recipe["pre_trial_steps"]}
    per_trial_vars = {registry[step["result_index"]] for step in recipe["per_trial_steps"]}

    assert "a" in pre_trial_vars
    assert "b_sto" in per_trial_vars
    assert "result" in per_trial_vars


def test_dead_code_elimination_with_conditionals():
    """
    Validates that if a conditional expression is calculated but never used,
    it gets eliminated by the optimizer.
    """
    script = """
    @iterations=1
    @output=final_result
    let a = 10
    let b = 20
    let unused_choice = if a > b then a else b
    let final_result = 100
    """
    recipe = compile_valuascript(script, optimize=True)
    assert recipe is not None

    # After DCE, only the live variable 'final_result' should remain.
    assert set(recipe["variable_registry"]) == {"final_result"}
