import pytest
import sys
import os
from lark.exceptions import UnexpectedInput

# Allow the test file to import 'vsc.py'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vsc import Lark, ValuaScriptTransformer, validate_recipe, ValuaScriptError, FUNCTION_SIGNATURES

# --- Test Setup ---
grammar_path = os.path.join(os.path.dirname(__file__), "..", "valuascript.lark")
with open(grammar_path, "r") as f:
    valuascript_grammar = f.read()
lark_parser = Lark(valuascript_grammar, start="start", parser="lalr")


@pytest.fixture
def base_script():
    """Provides a minimal, valid script header for tests."""
    return "@iterations = 100\n@output = result\n"


def compile_and_validate(script_body):
    """A helper to run the full compilation and validation pipeline."""
    raw_recipe = ValuaScriptTransformer().transform(lark_parser.parse(script_body))
    return validate_recipe(raw_recipe)


# =============================================================================
# --- "Happy Path" and Resilience Tests ---
# =============================================================================
def test_valid_scripts_compile_successfully():
    # Test a simple script
    compile_and_validate("@iterations=1\n@output=x\nlet x = 1")
    # Test variable-to-variable assignment (identity function)
    compile_and_validate("@iterations=1\n@output=y\nlet x=1\nlet y=x")
    # Test a more complex, multi-step script
    compile_and_validate(
        """
        @iterations=100
        @output=pres_val
        let cf = grow_series(100, 0.1, 5)
        let rate = 0.08
        let pres_val = npv(rate, cf)
    """
    )
    # Test a complex nested script
    compile_and_validate("@iterations=1\n@output=x\nlet x = sum_series(grow_series(1, 1, 1))")


def test_compiler_resilience_to_formatting():
    """Ensures comments and extra whitespace are handled gracefully."""
    script = """
    # This is a test model
    @iterations = 100
    @output     = final_value   # Set the output

    let initial = 10
    let rate    = 0.5
    
    # Calculate the result with extra spaces
    let final_value = initial   * (1 + rate)
    """
    assert compile_and_validate(script) is not None


def test_variable_name_shadowing_function_name():
    """Ensures a user can define a variable with the same name as a function."""
    script = """
    @iterations = 1
    @output = y
    let Normal = 10  # Define a variable that shadows the 'Normal' function
    let x = 5
    let y = Normal + x # Should be treated as 10 + 5
    """
    # This should compile because 'Normal' in the expression refers to the variable.
    # The type checker correctly infers that `Normal` is a scalar.
    assert compile_and_validate(script) is not None


# =============================================================================
# --- Syntax and Structural Error Tests ---
# =============================================================================
@pytest.mark.parametrize("malformed_snippet", ["let = 100", "let v 100", "let v = ", "let x = (1+2", "let x = [1,2", '@iterations="abc"'])
def test_syntax_errors(base_script, malformed_snippet):
    if malformed_snippet.startswith("@"):
        script = malformed_snippet + "\n@output=x\nlet x=1"
    else:
        script = base_script.replace("result", "my_var") + malformed_snippet
    with pytest.raises(UnexpectedInput):
        lark_parser.parse(script)


@pytest.mark.parametrize(
    "description, script_body, expected_error",
    [
        ("NEW: Empty file", "", "The @iterations directive is mandatory"),
        ("NEW: Directives only", "@iterations=1\n@output=x", "The final @output variable 'x' is not defined"),
    ],
)
def test_structural_integrity_errors(description, script_body, expected_error):
    with pytest.raises(ValuaScriptError, match=expected_error):
        compile_and_validate(script_body)


# =============================================================================
# --- Semantic, Type, and Arity Error Tests ---
# =============================================================================
@pytest.mark.parametrize(
    "description, script_body, expected_error",
    [
        ("Missing @iterations", "@output=x\nlet x=1", "The @iterations directive is mandatory"),
        ("Wrong @iterations type", "@iterations=1.5\n@output=x\nlet x=1", "must be a whole number"),
        ("Undefined output var", "@iterations=1\n@output=z\nlet x=1", "The final @output variable 'z' is not defined"),
        ("Undefined variable in assignment", "@iterations=1\n@output=y\nlet y=x", "Variable 'x' used in function 'identity' is not defined"),
        ("Undefined variable in function", "@iterations=1\n@output=y\nlet y=log(x)", "Variable 'x' used in function 'log' is not defined"),
        ("Unknown function", "@iterations=1\n@output=x\nlet x = unknown()", "Unknown function 'unknown'"),
        ("Scalar expected, vector var", "let v=[1]\nlet result=Normal(1,v)", "expects a 'scalar', but got a 'vector'"),
        ("Vector expected, scalar var", "let s=1\nlet result=sum_series(s)", "expects a 'vector', but got a 'scalar'"),
        ("Variadic type error", "let v=[1]\nlet result=compose_vector(1,v)", "expects a 'scalar', but got a 'vector'"),
    ],
)
def test_semantic_and_type_errors(base_script, description, script_body, expected_error):
    full_script = script_body if "let result" not in script_body else base_script + script_body
    with pytest.raises(ValuaScriptError, match=expected_error):
        compile_and_validate(full_script)


# --- Exhaustive Arity Checks ---
def get_arity_test_cases():
    for func, sig in FUNCTION_SIGNATURES.items():
        if sig.get("variadic", False):
            continue
        expected_argc = len(sig["arg_types"])
        if expected_argc > 0:
            yield pytest.param(func, expected_argc - 1, id=f"{func}-too_few")
        yield pytest.param(func, expected_argc + 1, id=f"{func}-too_many")


@pytest.mark.parametrize("func, provided_argc", get_arity_test_cases())
def test_all_function_arities(base_script, func, provided_argc):
    args = ", ".join(["1"] * provided_argc) if provided_argc > 0 else ""
    script = base_script + f"let result = {func}({args})"
    expected_argc = len(FUNCTION_SIGNATURES[func]["arg_types"])
    expected_error = f"Function '{func}' expects {expected_argc} argument"
    with pytest.raises(ValuaScriptError, match=expected_error):
        compile_and_validate(script)


def test_unused_variable_warning(capsys):
    """
    Tests that the compiler prints a warning for unused variables but still
    compiles successfully. `capsys` is a pytest fixture to capture stdout.
    """
    script = """
    @iterations = 1
    @output = b
    let a = 10  # This variable is unused
    let b = 20
    let c = 30  # This one is also unused
    """
    # Compilation should succeed (no exception)
    result = compile_and_validate(script)
    assert result is not None
    assert result["output_variable"] == "b"

    # Capture the standard output
    captured = capsys.readouterr()
    stdout = captured.out

    # Check that the warnings are present in the output
    assert "--- Compiler Warnings ---" in stdout
    assert "Warning: Variable 'a' was defined on line 4 but was never used." in stdout
    assert "Warning: Variable 'c' was defined on line 6 but was never used." in stdout

    # Check that the output variable 'b' is NOT warned about
    assert "Warning: Variable 'b'" not in stdout
