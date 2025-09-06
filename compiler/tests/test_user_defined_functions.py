import pytest
import sys
import os

# Make the compiler module available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
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
    recipe = compile_valuascript(script)
    assert recipe is not None
    # Check that inlining happened and the final result is correct
    registry = recipe["variable_registry"]
    assert "result" in registry
    # A simple check for inlining artifacts (mangled variable names)
    assert any("__add_one_1__x" in var_name for var_name in registry)


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
    recipe = compile_valuascript(script)
    assert recipe is not None
    registry = recipe["variable_registry"]
    assert "result" in registry
    assert any("__scale_1__v" in var_name for var_name in registry)
    assert any("__scale_1__factor" in var_name for var_name in registry)


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
    recipe = compile_valuascript(script)
    assert recipe is not None
    registry = recipe["variable_registry"]
    assert "result" in registry
    # Check for mangling of the first and second call
    assert any("__my_add_1__a" in var_name for var_name in registry)
    assert any("__my_add_2__a" in var_name for var_name in registry)


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
    recipe = compile_valuascript(script)
    assert recipe is not None
    assert "result" in recipe["variable_registry"]


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
        compile_valuascript(script)


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
        compile_valuascript(script)


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
        compile_valuascript(script)


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
        compile_valuascript(script)


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
        compile_valuascript(script)


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
    recipe = compile_valuascript(script)
    assert recipe is not None
    # Check that inlining was recursive
    all_vars = set(recipe["variable_registry"])
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
        compile_valuascript(script)


def test_mutual_recursion_error():
    script = """
    @iterations=1
    @output=result
    func f1(x: scalar) -> scalar { return f2(x) }
    func f2(x: scalar) -> scalar { return f1(x) }
    let result = f1(10)
    """
    with pytest.raises(ValuaScriptError, match="Recursive function call detected: f1 -> f2 -> f1"):
        compile_valuascript(script)


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
    recipe = compile_valuascript(script)
    assert recipe is not None
    registry = recipe["variable_registry"]
    per_trial_vars = {registry[step["result_index"]] for step in recipe["per_trial_steps"]}
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
    recipe = compile_valuascript(script)
    assert recipe is not None
    registry = recipe["variable_registry"]
    per_trial_vars = {registry[step["result_index"]] for step in recipe["per_trial_steps"]}
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
    recipe = compile_valuascript(script, optimize=True)
    assert recipe is not None
    all_vars = set(recipe["variable_registry"])
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
    recipe = compile_valuascript(script, optimize=True)
    assert recipe is not None
    assert set(recipe["variable_registry"]) == {"result"}


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
    recipe = compile_valuascript(script, optimize=True)
    assert recipe is not None
    all_vars = set(recipe["variable_registry"])
    # The mangled variable for the unused local should have been eliminated
    assert "__my_func_1__unused_local" not in all_vars
    # The used parameter and the final result should still be present
    assert "__my_func_1__x" in all_vars
    assert "result" in all_vars


def test_script_with_only_uncalled_udf_fails():
    script = "func uncalled(x: scalar) -> scalar { return x }"
    with pytest.raises(ValuaScriptError, match="The @iterations directive is mandatory"):
        compile_valuascript(script)
