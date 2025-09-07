import pytest
import sys
import os

# Make the compiler module available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError
from lark.exceptions import UnexpectedInput, UnexpectedToken, UnexpectedCharacters

# --- 1. VALID MODULE DEFINITIONS ---


def test_valid_module_compiles_successfully():
    """
    Tests that a valid module file with only function definitions compiles
    without error and produces an empty, non-runnable recipe.
    """
    script = """
    @module

    func add_one(x: scalar) -> scalar {
        \"\"\"Adds one to the input.\"\"\"
        return x + 1
    }

    func scale_vec2(v: vector, factor: scalar) -> vector {
        return v * factor
    }
    """
    recipe = compile_valuascript(script)
    assert recipe is not None
    # A valid module should produce a recipe with no steps and no output variable
    assert recipe["simulation_config"] == {}
    assert recipe["variable_registry"] == []
    assert recipe["output_variable_index"] is None
    assert recipe["pre_trial_steps"] == []
    assert recipe["per_trial_steps"] == []


def test_empty_module_is_valid():
    """An empty file with just the @module directive is valid."""
    script = "@module"
    recipe = compile_valuascript(script)
    assert recipe is not None
    assert recipe["variable_registry"] == []


# --- 2. INVALID MODULE STRUCTURE AND DIRECTIVES ---


@pytest.mark.parametrize(
    "script, error_match",
    [
        pytest.param("@module\nlet x = 1", "Global 'let' statements are not allowed in a module file", id="global_let_statement"),
        pytest.param("@module\n@iterations = 100", "The @iterations directive is not allowed when @module is declared", id="disallowed_iterations"),
        pytest.param("@module\n@output = x", "The @output directive is not allowed when @module is declared", id="disallowed_output"),
        pytest.param('@module\n@output_file = "f.csv"', "The @output_file directive is not allowed when @module is declared", id="disallowed_output_file"),
        pytest.param("@module = 1", "The @module directive does not accept a value", id="module_with_value"),
    ],
)
def test_invalid_module_structure(script, error_match):
    """
    Validates that the compiler rejects modules containing disallowed
    elements like global variables or execution directives.
    """
    # Add a dummy function to some tests to ensure the check isn't trivial
    if "let" in script:
        script += "\nfunc dummy() -> scalar { return 1 }"

    with pytest.raises(ValuaScriptError, match=error_match):
        compile_valuascript(script)


# --- 3. SEMANTIC AND SYNTAX ERRORS INSIDE A MODULE'S FUNCTIONS ---
# These tests ensure that even though a module isn't executed directly, the
# functions it contains are still fully validated for correctness.


def test_duplicate_function_names_in_module():
    script = """
    @module
    func my_func(a: scalar) -> scalar { return a }
    func my_func(b: vector) -> vector { return b }
    """
    with pytest.raises(ValuaScriptError, match="Function 'my_func' is defined more than once"):
        compile_valuascript(script)


def test_redefining_builtin_function_in_module():
    script = """
    @module
    func Normal(a: scalar, b: scalar) -> scalar {
        return a + b
    }
    """
    with pytest.raises(ValuaScriptError, match="Cannot redefine built-in function 'Normal'"):
        compile_valuascript(script)


@pytest.mark.parametrize(
    "func_body, error_match",
    [
        # Scoping and Declaration Errors
        pytest.param("let a = 10\nreturn a", "Variable 'a' is defined more than once in function 'test_func'", id="redeclare_param_in_body"),
        pytest.param("let x = 1\nlet x = 2\nreturn x", "Variable 'x' is defined more than once in function 'test_func'", id="redeclare_local_var"),
        pytest.param("return undefined_var", "Variable 'undefined_var' used in function 'identity' is not defined", id="reference_undefined_var"),
        # Type Errors
        pytest.param("let v = [1]\nreturn log(v)", "Argument 1 for 'log' expects a 'scalar', but got a 'vector'", id="type_mismatch_builtin"),
        pytest.param("return 1", "Function 'test_func' returns type 'scalar' but is defined to return 'vector'", id="return_type_mismatch"),
        # Arity Errors
        pytest.param("return log(1, 2)", "Function 'log' expects 1 argument\\(s\\), but got 2", id="arity_mismatch_too_many"),
        # Missing Return
        pytest.param("let x = a + 1", "Function 'test_func' is missing a return statement", id="missing_return"),
        # Unknown Function
        pytest.param("return unknown_func(a)", "Unknown function 'unknown_func'", id="unknown_function_call"),
    ],
)
def test_semantic_errors_inside_module_function_body(func_body, error_match):
    """
    Ensures the compiler's semantic validation is correctly applied to the
    body of functions defined within a module.
    """
    # The return type is set to vector for the return mismatch test
    return_type = "vector" if "returns type 'scalar'" in error_match else "scalar"
    script = f"""
    @module
    func test_func(a: scalar) -> {return_type} {{
        {func_body}
    }}
    """
    with pytest.raises(ValuaScriptError, match=error_match):
        compile_valuascript(script)


def test_syntax_error_inside_module_function_body():
    """Checks that low-level syntax errors are caught within a module's function."""
    script = """
    @module
    func test_syntax() -> scalar {
        let x = (1 + 2
        return x
    }
    """
    with pytest.raises((ValuaScriptError, UnexpectedInput, UnexpectedCharacters, UnexpectedToken)):
        compile_valuascript(script)


# --- 4. RECURSION CHECKS IN MODULES ---


def test_direct_recursion_in_module():
    script = """
    @module
    func factorial(n: scalar) -> scalar {
        return n * factorial(n - 1)
    }
    """
    with pytest.raises(ValuaScriptError, match="Recursive function call detected: factorial -> factorial"):
        compile_valuascript(script)


def test_mutual_recursion_in_module():
    script = """
    @module
    func f1(x: scalar) -> scalar { return f2(x) }
    func f2(x: scalar) -> scalar { return f1(x) }
    """
    with pytest.raises(ValuaScriptError, match="Recursive function call detected: f1 -> f2 -> f1"):
        compile_valuascript(script)


def test_deep_call_chain_validation_in_module():
    """
    Ensures that a type error deep within a call chain inside a module
    is still detected correctly by the validator.
    """
    script = """
    @module
    func f4(v: vector) -> scalar { return log(v) }
    func f3(s: scalar) -> scalar { return f4([s]) }
    func f2(s: scalar) -> scalar { return f3(s) }
    func f1(s: scalar) -> scalar { return f2(s) }
    """
    with pytest.raises(ValuaScriptError, match="Argument 1 for 'log' expects a 'scalar', but got a 'vector'"):
        compile_valuascript(script)
