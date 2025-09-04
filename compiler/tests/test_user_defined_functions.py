import pytest
import sys
import os

# Make the compiler module available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import validate_valuascript
from vsc.exceptions import ValuaScriptError
from lark.exceptions import UnexpectedInput, UnexpectedToken, UnexpectedCharacters

# Base script setup for tests
BASE_SCRIPT = "@iterations=1\n@output=result\n"


# --- 1. VALID FUNCTION DEFINITIONS AND CALLS ---


def test_valid_scalar_function_with_docstring():
    script = """
    @iterations=1
    @output=result
    func add_one(x: scalar) -> scalar {
        \"\"\"Adds one to a scalar.\"\"\"
        return x + 1
    }
    let result = add_one(10)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    # Check that inlining happened and the final result is correct
    assert recipe["output_variable"] == "result"
    # A simple check for inlining artifacts
    assert any("__add_one_1__x" in step["result"] for step in recipe["pre_trial_steps"])


def test_valid_vector_function_without_docstring():
    """Explicitly test that a function without a docstring is valid."""
    script = """
    @iterations=1
    @output=result
    func scale(v: vector, factor: scalar) -> vector {
        let scaled_v = v * factor
        return scaled_v
    }
    let my_vec = [1, 2, 3]
    let result = scale(my_vec, 10)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    assert recipe["output_variable"] == "result"
    assert any("__scale_1__v" in step["result"] for step in recipe["pre_trial_steps"])
    assert any("__scale_1__factor" in step["result"] for step in recipe["pre_trial_steps"])


def test_multiple_calls_to_same_function():
    script = """
    @iterations=1
    @output=result
    func my_add(a: scalar, b: scalar) -> scalar {
        return a + b
    }
    let x = my_add(1, 2)
    let y = my_add(x, 10)
    let result = y
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    assert recipe["output_variable"] == "result"
    # Check for mangling of the first and second call
    assert any("__my_add_1__a" in step["result"] for step in recipe["pre_trial_steps"])
    assert any("__my_add_2__a" in step["result"] for step in recipe["pre_trial_steps"])


def test_function_calling_builtin():
    script = """
    @iterations=1
    @output=result
    func present_value(rate: scalar, cashflows: vector) -> scalar {
        return npv(rate, cashflows)
    }
    let cf = [10, 20]
    let result = present_value(0.1, cf)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    assert recipe["output_variable"] == "result"


# --- 2. SYNTAX ERRORS IN FUNCTION DEFINITION ---


@pytest.mark.parametrize(
    "func_snippet",
    [
        pytest.param("func test(a: scalar) scalar { return a }", id="missing_arrow"),
        pytest.param("func test(a scalar) -> scalar { return a }", id="missing_colon"),
        pytest.param("func test(a: scalar) -> { return a }", id="missing_return_type"),
        pytest.param("func test(a: scalar) -> scalar return a }", id="missing_opening_brace"),
        pytest.param("func test(a: scalar) -> scalar { return a", id="missing_closing_brace"),
    ],
)
def test_syntax_errors_in_definition(func_snippet):
    script = f"{BASE_SCRIPT}{func_snippet}\nlet result = 1"
    # Lark errors can be of different types depending on what's missing
    with pytest.raises((UnexpectedInput, UnexpectedToken, UnexpectedCharacters)):
        validate_valuascript(script)


# --- 3. SEMANTIC ERRORS (TYPE MISMATCHES, ETC.) ---


@pytest.mark.parametrize(
    "script_body, error_match",
    [
        # Missing return
        pytest.param("func test(a: scalar) -> scalar { let x = a }", "Function 'test' is missing a return statement.", id="missing_return"),
        # Return type mismatch
        pytest.param("func test(a: scalar) -> vector { return a }", "Function 'test' returns type 'scalar' but is defined to return 'vector'", id="return_type_mismatch_scalar_for_vector"),
        pytest.param("func test(a: vector) -> scalar { return a }", "Function 'test' returns type 'vector' but is defined to return 'scalar'", id="return_type_mismatch_vector_for_scalar"),
        # Argument type mismatch
        pytest.param(
            "func test(a: scalar) -> scalar { return a }\nlet v = [1]\nlet result = test(v)", "Argument 1 for 'test' expects a 'scalar', but got a 'vector'", id="arg_type_mismatch_vector_for_scalar"
        ),
        pytest.param(
            "func test(a: vector) -> vector { return a }\nlet s = 1\nlet result = test(s)", "Argument 1 for 'test' expects a 'vector', but got a 'scalar'", id="arg_type_mismatch_scalar_for_vector"
        ),
        # Wrong number of arguments
        pytest.param("func test(a: scalar) -> scalar { return a }\nlet result = test(1, 2)", "Function 'test' expects 1 argument\\(s\\), but got 2", id="too_many_args"),
        pytest.param("func test(a: scalar, b: scalar) -> scalar { return a }\nlet result = test(1)", "Function 'test' expects 2 argument\\(s\\), but got 1", id="too_few_args"),
        # Using result of UDF incorrectly
        pytest.param(
            "func get_s() -> scalar { return 1 }\nlet r = get_s()\nlet result = sum_series(r)",
            "Argument 1 for 'sum_series' expects a 'vector', but got a 'scalar'",
            id="udf_result_misuse_scalar_for_vector",
        ),
        pytest.param(
            "func get_v() -> vector { return [1] }\nlet r = get_v()\nlet result = log(r)", "Argument 1 for 'log' expects a 'scalar', but got a 'vector'", id="udf_result_misuse_vector_for_scalar"
        ),
    ],
)
def test_semantic_type_errors(script_body, error_match):
    script = f"{BASE_SCRIPT}{script_body}"
    with pytest.raises(ValuaScriptError, match=error_match):
        validate_valuascript(script)


# --- 4. SCOPING AND VARIABLE DECLARATION ERRORS ---


@pytest.mark.parametrize(
    "script_body, error_match",
    [
        # Double declaration
        pytest.param("func test(a: scalar) -> scalar { let a = 10\nreturn a }", "Variable 'a' is defined more than once in function 'test'", id="redeclare_param"),
        pytest.param("func test(a: scalar) -> scalar { let x = 1\nlet x = 2\nreturn x }", "Variable 'x' is defined more than once in function 'test'", id="redeclare_local_var"),
        # Undefined variable reference
        pytest.param("func test(a: scalar) -> scalar { return b }", "Variable 'b' used in function 'identity' is not defined", id="reference_undefined_var"),
        pytest.param("func test(a: scalar) -> scalar { return a + global_var }\nlet global_var=10", "Variable 'global_var' used in function 'add' is not defined", id="reference_global_var_is_error"),
        # Redefining built-in
        pytest.param("func log(a: scalar) -> scalar { return a }", "Cannot redefine built-in function 'log'", id="redefine_builtin_function"),
    ],
)
def test_scoping_and_declaration_errors(script_body, error_match):
    # Need to add a dummy `let result = 1` for some cases to be valid structurally
    script = f"{BASE_SCRIPT}{script_body}\nlet result = 1"
    with pytest.raises(ValuaScriptError, match=error_match):
        validate_valuascript(script)


# --- 5. VALIDATION CONSISTENCY (ERRORS INSIDE FUNCTION BODY) ---


@pytest.mark.parametrize(
    "func_body, error_match",
    [
        pytest.param("let x = unknown_func()\nreturn x", "Unknown function 'unknown_func'", id="body_unknown_function"),
        pytest.param("let v = [1]\nlet x = log(v)\nreturn x", "Argument 1 for 'log' expects a 'scalar', but got a 'vector'", id="body_type_error_builtin"),
    ],
)
def test_validation_consistency_inside_body(func_body, error_match):
    """
    Ensures that the semantic validation logic for the main script is also applied
    identically inside a function's body.
    """
    script = f"""
    @iterations=1
    @output=result
    func test() -> scalar {{
        {func_body}
    }}
    let result = test()
    """
    with pytest.raises(ValuaScriptError, match=error_match):
        validate_valuascript(script)


def test_syntax_errors_inside_body():
    """
    Ensures that low-level syntax errors inside a function body are caught
    by the parser or pre-parser, raising any of the expected exception types.
    """
    script = """
    @iterations=1
    @output=result
    func test() -> scalar {
        let x = 1 +
        return x
    }
    let result = test()
    """
    with pytest.raises((ValuaScriptError, UnexpectedCharacters, UnexpectedToken, UnexpectedInput)):
        validate_valuascript(script)


# --- 6. INTER-FUNCTION CALLS AND RECURSION ---


def test_udf_calling_another_udf():
    script = """
    @iterations=1
    @output=result
    func double(x: scalar) -> scalar { return x * 2 }
    func add_and_double(a: scalar, b: scalar) -> scalar {
        let s = a + b
        return double(s)
    }
    let result = add_and_double(10, 20)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    # Check that inlining was recursive
    all_vars = {step["result"] for step in recipe["pre_trial_steps"]}
    assert "__add_and_double_1__s" in all_vars
    # The call to double() inside add_and_double() gets its own unique mangling
    assert any(key.startswith("__double_") for key in all_vars)


def test_direct_recursion_error():
    script = """
    @iterations=1
    @output=result
    func recursive(x: scalar) -> scalar {
        return recursive(x - 1)
    }
    let result = recursive(10)
    """
    with pytest.raises(ValuaScriptError, match="Recursive function call detected: recursive -> recursive"):
        validate_valuascript(script)


def test_mutual_recursion_error():
    script = """
    @iterations=1
    @output=result
    func f1(x: scalar) -> scalar { return f2(x) }
    func f2(x: scalar) -> scalar { return f1(x) }
    let result = f1(10)
    """
    with pytest.raises(ValuaScriptError, match="Recursive function call detected: f1 -> f2 -> f1"):
        validate_valuascript(script)


# --- 7. STOCHASTICITY PROPAGATION ---


def test_stochastic_function_taints_caller():
    """
    CRITICAL TEST: Ensures that if a UDF is stochastic, the variable
    that calls it also becomes stochastic.
    """
    script = """
    @iterations=1
    @output=result
    func get_random() -> scalar {
        let r = Normal(10, 1)
        return r
    }
    let sto = get_random()
    let result = sto + 10
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    per_trial_vars = {step["result"] for step in recipe["per_trial_steps"]}
    # Check that all relevant variables were moved to the per_trial phase
    assert "__get_random_1__r" in per_trial_vars
    assert "sto" in per_trial_vars
    assert "result" in per_trial_vars


def test_deterministic_function_with_stochastic_input():
    script = """
    @iterations=1
    @output=result
    func add_one(x: scalar) -> scalar { return x + 1 }
    let rand_in = Normal(10, 1)
    let result = add_one(rand_in)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    per_trial_vars = {step["result"] for step in recipe["per_trial_steps"]}
    assert "rand_in" in per_trial_vars
    assert "result" in per_trial_vars
    assert "__add_one_1__x" in per_trial_vars


# --- 8. INTERACTION WITH OPTIMIZATIONS (DEAD CODE ELIMINATION) ---


def test_dce_removes_unused_udf_call():
    script = """
    @iterations=1
    @output=result
    func my_func(x: scalar) -> scalar {
        let y = x * 1000
        return y
    }
    let unused = my_func(10)
    let result = 42
    """
    recipe = validate_valuascript(script, optimize=True)
    assert recipe is not None
    all_vars = {step["result"] for step in recipe["pre_trial_steps"]}
    assert all_vars == {"result"}
    assert "unused" not in all_vars
    assert "__my_func_1__x" not in all_vars
    assert "__my_func_1__y" not in all_vars


def test_dce_ignores_uncalled_udf():
    script = """
    @iterations=1
    @output=result
    func uncalled(x: scalar) -> scalar { return x }
    let result = 100
    """
    recipe = validate_valuascript(script, optimize=True)
    assert recipe is not None
    assert {step["result"] for step in recipe["pre_trial_steps"]} == {"result"}


# --- 9. TRIVIAL AND COMPLEX BODY STRUCTURES ---


def test_function_with_no_params():
    script = """
    @iterations=1
    @output=result
    func get_pi() -> scalar { return 3.14 }
    let result = get_pi()
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    assert recipe["output_variable"] == "result"


def test_function_with_only_return():
    script = """
    @iterations=1
    @output=result
    func my_identity(v: vector) -> vector {
        return v
    }
    let my_vec = [1, 2]
    let result = my_identity(my_vec)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    assert any("__my_identity_1__v" in step["result"] for step in recipe["pre_trial_steps"])


def test_function_with_complex_return_expression():
    script = """
    @iterations=1
    @output=result
    func calc(a: scalar, b: scalar) -> scalar {
        return log(a + (b * 2))
    }
    let result = calc(10, 5)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    assert recipe["output_variable"] == "result"


# --- 10. ADVANCED NESTING AND EDGE CASES ---


def test_deeply_nested_udf_calls():
    script = """
    @iterations=1
    @output=result
    func f1(x: scalar) -> scalar { return x + 1 }
    func f2(x: scalar) -> scalar { return f1(x) * 2 }
    func f3(x: scalar) -> scalar { return f2(x) + 3 }
    let result = f3(10)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    all_vars = {step["result"] for step in recipe["pre_trial_steps"]}
    assert "result" in all_vars
    assert any(key.startswith("__f1_") for key in all_vars)
    assert any(key.startswith("__f2_") for key in all_vars)
    assert any(key.startswith("__f3_") for key in all_vars)


def test_multiple_nested_udf_arguments():
    script = """
    @iterations=1
    @output=result
    func double(x: scalar) -> scalar { return x * 2 }
    func triple(x: scalar) -> scalar { return x * 3 }
    let result = double(5) + triple(10)
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    # Check that temporary variables for the flattened calls were created
    all_vars = {step["result"] for step in recipe["pre_trial_steps"]}
    assert any(key.startswith("__temp_") for key in all_vars)


def test_udf_returning_literal():
    script = """
    @iterations=1
    @output=result
    func get_magic_number() -> scalar { return 42 }
    let result = get_magic_number()
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    result_step = next(step for step in recipe["pre_trial_steps"] if step["result"] == "result")
    # The call should be inlined to a direct literal assignment
    assert result_step["type"] == "literal_assignment"
    assert result_step["value"] == 42


def test_dce_on_unused_local_vars_in_udf():
    script = """
    @iterations=1
    @output=result
    func my_func(x: scalar) -> scalar {
        let unused_local = x * 1000
        return x + 1
    }
    let result = my_func(10)
    """
    recipe = validate_valuascript(script, optimize=True)
    assert recipe is not None
    all_vars = {step["result"] for step in recipe["pre_trial_steps"]}
    # The mangled variable for the unused local should have been eliminated
    assert "__my_func_1__unused_local" not in all_vars
    # The used parameter and the final result should still be present
    assert "__my_func_1__x" in all_vars
    assert "result" in all_vars


def test_stochasticity_through_deep_nesting():
    script = """
    @iterations=1
    @output=result
    func f1() -> scalar { return Normal(100, 1) }
    func f2() -> scalar { return f1() * 2 }
    func f3() -> scalar { return f2() + 3 }
    let result = f3()
    """
    recipe = validate_valuascript(script)
    assert recipe is not None
    # After full inlining, the crucial part is that ALL variables should be
    # stochastic because the chain starts with Normal().
    all_vars_in_recipe = {step["result"] for step in recipe["pre_trial_steps"]} | {step["result"] for step in recipe["per_trial_steps"]}
    per_trial_vars = {step["result"] for step in recipe["per_trial_steps"]}
    # Assert that the final output variable is correctly marked as stochastic.
    assert "result" in per_trial_vars
    # Assert that there are NO pre-trial steps.
    assert not recipe["pre_trial_steps"]
    # Assert that all variables created during compilation are in the per-trial set.
    # This proves the "taint" propagated correctly through the entire chain.
    assert all_vars_in_recipe == per_trial_vars


def test_script_with_only_uncalled_udf_fails():
    script = "func uncalled(x: scalar) -> scalar { return x }"
    with pytest.raises(ValuaScriptError, match="The @iterations directive is mandatory"):
        validate_valuascript(script)
