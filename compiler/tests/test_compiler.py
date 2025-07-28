# compiler/tests/test_compiler.py
# The final, exhaustive test suite for the ValuaScript compiler.

import pytest
import sys
import os
from lark.exceptions import UnexpectedInput

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vsc import Lark, ValuaScriptTransformer, validate_recipe, ValuaScriptError, FUNCTION_SIGNATURES

# --- Test Setup ---
grammar_path = os.path.join(os.path.dirname(__file__), "..", "valuascript.lark")
with open(grammar_path, "r") as f:
    valuasc_grammar = f.read()
lark_parser = Lark(valuasc_grammar, start="start", parser="lalr")


@pytest.fixture
def base_script():
    """Provides a minimal, valid script header for tests."""
    return "@iterations = 100\n@output = result\n"


def compile_and_validate(script_body):
    """A helper to run the full compilation and validation pipeline."""
    raw_recipe = ValuaScriptTransformer().transform(lark_parser.parse(script_body))
    return validate_recipe(raw_recipe)


# =============================================================================
# --- "Happy Path" Tests ---
# =============================================================================
def test_valid_scripts_compile_successfully():
    compile_and_validate("@iterations=1\n@output=x\nlet x = 1")
    compile_and_validate("@iterations=1\n@output=y\nlet x=1\nlet y=x")
    compile_and_validate(
        """
        @iterations=100
        @output=pres_val
        let cf = grow_series(100, 0.1, 5)
        let rate = 0.08
        let pres_val = npv(rate, cf)
    """
    )
    compile_and_validate("@iterations=1\n@output=x\nlet x = sum_series(grow_series(1, 1, 1))")


# =============================================================================
# --- Requirement #6: Syntax Error Tests ---
# =============================================================================
@pytest.mark.parametrize("malformed_snippet", ["let = 100", "let v 100", "let v = ", "let x = (1+2", "let x = [1,2", '@iterations="abc"'])
def test_syntax_errors(base_script, malformed_snippet):
    if malformed_snippet.startswith("@"):
        script = malformed_snippet + "\n@output=x\nlet x=1"
    else:
        script = base_script.replace("result", "my_var") + malformed_snippet
    with pytest.raises(UnexpectedInput):
        lark_parser.parse(script)


# =============================================================================
# --- Semantic, Type, and Arity Error Tests ---
# =============================================================================


@pytest.mark.parametrize(
    "description, script_body, expected_error",
    [
        # Req #1 & #3: Missing Directives
        ("Missing @iterations", "@output=x\nlet x=1", "The @iterations directive is mandatory"),
        ("Wrong @iterations type", "@iterations=1.5\n@output=x\nlet x=1", "must be a whole number"),
        ("Undefined output var", "@iterations=1\n@output=z\nlet x=1", "The final @output variable 'z' is not defined"),
        # Req #4: Undefined Variable (with corrected, more specific error messages)
        ("Undefined variable in assignment", "@iterations=1\n@output=y\nlet y=x", "Variable 'x' used in function 'identity' is not defined"),
        ("Undefined variable in function", "@iterations=1\n@output=y\nlet y=log(x)", "Variable 'x' used in function 'log' is not defined"),
        # Req #7: Unknown Function
        ("Unknown function", "@iterations=1\n@output=x\nlet x = unknown()", "Unknown function 'unknown'"),
        # Req #9: Type Errors
        ("Scalar expected, vector var", "let v=[1]\nlet result=Normal(1,v)", "expects a 'scalar', but got a 'vector'"),
        ("Vector expected, scalar var", "let s=1\nlet result=sum_series(s)", "expects a 'vector', but got a 'scalar'"),
        ("Variadic type error", "let v=[1]\nlet result=compose_vector(1,v)", "expects a 'scalar', but got a 'vector'"),
    ],
)
def test_semantic_and_type_errors(base_script, description, script_body, expected_error):
    if "let result" in script_body:
        full_script = base_script + script_body
    else:
        full_script = script_body
    with pytest.raises(ValuaScriptError, match=expected_error):
        compile_and_validate(full_script)


# --- Req #8: Exhaustive Arity Checks ---
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
