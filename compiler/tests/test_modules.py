import pytest
import sys
import os

# Make the compiler module available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode
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
    "script, expected_code",
    [
        pytest.param("@module\nlet x = 1", ErrorCode.GLOBAL_LET_IN_MODULE, id="global_let_statement"),
        pytest.param("@module\n@iterations = 100", ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, id="disallowed_iterations"),
        pytest.param("@module\n@output = x", ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, id="disallowed_output"),
        pytest.param('@module\n@output_file = "f.csv"', ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, id="disallowed_output_file"),
        pytest.param("@module = 1", ErrorCode.MODULE_WITH_VALUE, id="module_with_value"),
    ],
)
def test_invalid_module_structure(script, expected_code):
    """
    Validates that the compiler rejects modules containing disallowed
    elements like global variables or execution directives.
    """
    # Add a dummy function to some tests to ensure the check isn't trivial
    if "let" in script:
        script += "\nfunc dummy() -> scalar { return 1 }"

    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == expected_code


# --- 3. SEMANTIC AND SYNTAX ERRORS INSIDE A MODULE'S FUNCTIONS ---
# These tests ensure that even though a module isn't executed directly, the
# functions it contains are still fully validated for correctness.


def test_duplicate_function_names_in_module():
    script = """
    @module
    func my_func(a: scalar) -> scalar { return a }
    func my_func(b: vector) -> vector { return b }
    """
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.DUPLICATE_FUNCTION


def test_redefining_builtin_function_in_module():
    script = """
    @module
    func Normal(a: scalar, b: scalar) -> scalar {
        return a + b
    }
    """
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.REDEFINE_BUILTIN_FUNCTION


@pytest.mark.parametrize(
    "func_body, expected_code",
    [
        pytest.param("let a = 10\nreturn a", ErrorCode.DUPLICATE_VARIABLE_IN_FUNC, id="redeclare_param_in_body"),
        pytest.param("let x = 1\nlet x = 2\nreturn x", ErrorCode.DUPLICATE_VARIABLE_IN_FUNC, id="redeclare_local_var"),
        pytest.param("return undefined_var", ErrorCode.UNDEFINED_VARIABLE_IN_FUNC, id="reference_undefined_var"),
        pytest.param("let v = [1]\nreturn log(v)", ErrorCode.ARGUMENT_TYPE_MISMATCH, id="type_mismatch_builtin"),
        pytest.param("return 1", ErrorCode.RETURN_TYPE_MISMATCH, id="return_type_mismatch"),
        pytest.param("return log(1, 2)", ErrorCode.ARGUMENT_COUNT_MISMATCH, id="arity_mismatch_too_many"),
        pytest.param("let x = a + 1", ErrorCode.MISSING_RETURN_STATEMENT, id="missing_return"),
        pytest.param("return unknown_func(a)", ErrorCode.UNKNOWN_FUNCTION, id="unknown_function_call"),
    ],
)
def test_semantic_errors_inside_module_function_body(func_body, expected_code):
    """
    Ensures the compiler's semantic validation is correctly applied to the
    body of functions defined within a module.
    """
    return_type = "vector" if expected_code == ErrorCode.RETURN_TYPE_MISMATCH else "scalar"
    script = f"""
    @module
    func test_func(a: scalar) -> {return_type} {{
        {func_body}
    }}
    """
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == expected_code


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
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.RECURSIVE_CALL_DETECTED


def test_mutual_recursion_in_module():
    script = """
    @module
    func f1(x: scalar) -> scalar { return f2(x) }
    func f2(x: scalar) -> scalar { return f1(x) }
    """
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.RECURSIVE_CALL_DETECTED


def test_deep_call_chain_validation_in_module():
    """
    Ensures that a type error deep within a call chain inside a module
    is still detected correctly by the validator.
    """
    script = """
    @module
    func f4(v: vector) -> scalar { return log(v) } # This is the error
    func f3(s: scalar) -> scalar { return f4([s]) }
    func f2(s: scalar) -> scalar { return f3(s) }
    func f1(s: scalar) -> scalar { return f2(s) }
    """
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.ARGUMENT_TYPE_MISMATCH
