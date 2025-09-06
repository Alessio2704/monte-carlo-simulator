import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lark.exceptions import UnexpectedToken, UnexpectedInput, UnexpectedCharacters
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError
from vsc.config import FUNCTION_SIGNATURES


@pytest.fixture
def base_script():
    return "@iterations = 100\n@output = result\n"


def test_valid_scripts_compile_successfully():
    compile_valuascript("@iterations=1\n@output=x\nlet x = 1")
    compile_valuascript("@iterations=1\n@output=y\nlet x=1\nlet y=x")
    compile_valuascript(
        """
        @iterations=100
        @output=pres_val
        let cf = grow_series(100, 0.1, 5)
        let rate = 0.08
        let pres_val = npv(rate, cf)
        """
    )
    compile_valuascript("@iterations=1\n@output=x\nlet x = sum_series(grow_series(1, 1, 1))")
    compile_valuascript('@iterations=1\n@output=x\n@output_file="f.csv"\nlet x = 1')
    compile_valuascript("@iterations=1\n@output=v\nlet my_vec = [1,2,3]\nlet v = delete_element(my_vec, 1)")
    compile_valuascript("@iterations=1\n@output=x\nlet my_vec=[100,200]\nlet x = my_vec[0]")
    compile_valuascript("@iterations=1\n@output=x\nlet my_vec=[100,200]\nlet i=1\nlet x = my_vec[i]")
    compile_valuascript("@iterations=1\n@output=x\nlet my_vec=[100,200]\nlet x = my_vec[1-1]")
    compile_valuascript("@iterations=1\n@output=x\nlet my_vec=[1,2,3]\nlet x = my_vec[:-1]")
    compile_valuascript("@iterations=1\n@output=x\nlet x = 1_000_000")
    compile_valuascript("@iterations=1\n@output=x\nlet x = 1_234.567_8")
    compile_valuascript("@iterations=1\n@output=x\nlet x = -5_000")

    script = """
    # This is a test model
    @iterations = 100
    @output     = final_value
    let initial = 10
    let rate    = 0.5
    let final_value = initial * (1 + rate)
    """
    assert compile_valuascript(script) is not None


@pytest.mark.parametrize(
    "malformed_snippet",
    [
        "leta = 1",
        "let = 100",
        "let v 100",
        "let v = ",
        "let x = (1+2",
        "let v = my_vec[0",
        "let x = 1__000",
        "let x = 100_",
        "let x = _100",
        "let x = 1._5",
        "let x = [1, 2, __3]",
    ],
)
def test_syntax_errors(malformed_snippet):
    # Test the snippet in isolation to ensure it fails on its own.
    script = f"@iterations=1\n@output=x\n{malformed_snippet}"
    with pytest.raises((UnexpectedToken, UnexpectedInput, UnexpectedCharacters, ValuaScriptError)):
        compile_valuascript(script)


@pytest.mark.parametrize(
    "script_body, expected_error",
    [
        ("", "The @iterations directive is mandatory"),
        ("@iterations=1\n@output=x", "The final @output variable 'x' is not defined"),
        ("let a = \n@iterations=1\n@output=a", "Missing value after '='."),
        ("@output = \n@iterations=1\nlet a=1", "Missing value after '='."),
        ("@iterations=1\n@output=a\nlet a", "Incomplete assignment."),
        ("@iterations=1\n@output=a\nlet", "Incomplete assignment."),
    ],
)
def test_structural_integrity_errors(script_body, expected_error):
    with pytest.raises(ValuaScriptError, match=expected_error):
        compile_valuascript(script_body)


@pytest.mark.parametrize(
    "script_body, expected_error",
    [
        ("@output=x\nlet x=1", "The @iterations directive is mandatory"),
        ("@iterations=1.5\n@output=x\nlet x=1", "must be a whole number"),
        ("@iterations=1\n@iterations=2\n@output=x\nlet x=1", "directive '@iterations' is defined more than once"),
        ("@iterations=1\n@output=x\nlet x=1\n@invalid=1", "Unknown directive '@invalid'"),
        ("@iterations=1\n@output=z\nlet x=1", "The final @output variable 'z' is not defined"),
        ("@iterations=1\n@output=y\nlet y=x", "Variable 'x' used in function 'identity' is not defined"),
        ("@iterations=1\n@output=y\nlet y=log(x)", "Variable 'x' used in function 'log' is not defined"),
        ("@iterations=1\n@output=x\nlet x = unknown()", "Unknown function 'unknown'"),
        ("@iterations=1\n@output=result\nlet v=[1]\nlet result=Normal(1,v)", "Argument 2 for 'Normal' expects a 'scalar', but got a 'vector'"),
        ("@iterations=1\n@output=x\nlet s=1\nlet v=grow_series(s,0,1)\nlet x=log(v)", "Argument 1 for 'log' expects a 'scalar', but got a 'vector'"),
        ("@iterations=1\n@output=x\nlet x=1\n@output_file=not_a_string", "must be a string literal"),
        ("@iterations=1\n@output=v\nlet s=1\nlet v=delete_element(s, 0)", "Argument 1 for 'delete_element' expects a 'vector', but got a 'scalar'"),
        ("@iterations=1\n@output=v\nlet my_vec=[1]\nlet v=delete_element(my_vec, [0])", "Argument 2 for 'delete_element' expects a 'scalar', but got a 'vector'"),
        ("@iterations=1\n@output=v\nlet s=1\nlet v=s[0]", "Argument 1 for 'get_element' expects a 'vector', but got a 'scalar'"),
        ("@iterations=1\n@output=v\nlet v=[1]\nlet i=[0]\nlet x=v[i]", "Argument 2 for 'get_element' expects a 'scalar', but got a 'vector'"),
        ("@iterations=1\n@output=x\nlet s=1\nlet x=s[:-1]", "Argument 1 for 'delete_element' expects a 'vector', but got a 'scalar'"),
        ("@iterations=1\n@output=x\nlet q=2\nlet x=[1,q]", "Invalid item q in vector literal for 'x'"),
        ('@iterations=1\n@output=x\nlet x=[1,"hello"]', "Invalid item \"hello\" in vector literal for 'x'"),
        ("@iterations=1\n@output=x\nlet x=[1, _3]", "Invalid item _3 in vector literal for 'x'"),
    ],
)
def test_semantic_errors(script_body, expected_error):
    with pytest.raises(ValuaScriptError, match=expected_error):
        compile_valuascript(script_body)


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
    args_list = []
    arg_types = FUNCTION_SIGNATURES[func]["arg_types"]
    for i in range(provided_argc):
        expected_type = arg_types[min(i, len(arg_types) - 1)] if arg_types else "any"
        args_list.append(f'"arg{i}"' if expected_type == "string" else "1")
    args = ", ".join(args_list) if provided_argc > 0 else ""
    script = base_script + f"let result = {func}({args})"
    expected_argc = len(FUNCTION_SIGNATURES[func]["arg_types"])
    expected_error = f"Function '{func}' expects {expected_argc} argument"
    with pytest.raises(ValuaScriptError, match=expected_error):
        compile_valuascript(script)


# ==============================================================================
# TESTS FOR LINKER AND BYTECODE GENERATION
# ==============================================================================


def test_linker_handles_nested_function_calls():
    """
    This is a regression test. It ensures that nested function calls in the AST
    are correctly typed in the final bytecode, preventing the
    'Argument object is missing 'type' field' error in the C++ engine.
    """
    script = """
    @iterations=1
    @output=result
    let base = 10
    let result = log(exp(base)) 
    """
    recipe = compile_valuascript(script)
    assert recipe is not None

    # Find the 'result' step in the bytecode
    registry = recipe["variable_registry"]
    result_index = registry.index("result")

    # ** THE FIX IS HERE **
    # The step could be in pre_trial or per_trial, so we search both.
    all_steps = recipe["pre_trial_steps"] + recipe["per_trial_steps"]
    result_step = next(s for s in all_steps if s["result_index"] == result_index)

    assert result_step is not None
    assert result_step["function"] == "log"
    assert len(result_step["args"]) == 1

    # The crucial assertion: check the nested argument
    nested_arg = result_step["args"][0]
    assert isinstance(nested_arg, dict)
    assert nested_arg.get("type") == "execution_assignment"
    assert nested_arg.get("function") == "exp"
    assert len(nested_arg.get("args", [])) == 1


# ==============================================================================
# TESTS FOR LOOP-INVARIANT CODE MOTION OPTIMIZATION
# ==============================================================================


@pytest.mark.parametrize(
    "script_body, expected_pre_trial_names, expected_per_trial_names",
    [
        pytest.param("let x = 10\nlet y = x + 5", ["x", "y"], [], id="all_deterministic"),
        pytest.param("let x = Normal(1,1)\nlet y = Pert(1,2,3)", [], ["x", "y"], id="all_stochastic"),
        pytest.param("let x = 100\nlet y = Normal(x, 10)", ["x"], ["y"], id="deterministic_feeds_stochastic"),
        pytest.param("let x = Normal(1,1)\nlet y = x + 10\nlet z = y * 2", [], ["x", "y", "z"], id="stochastic_taints_chain"),
    ],
)
def test_optimization_step_partitioning(script_body, expected_pre_trial_names, expected_per_trial_names):
    """
    Validates that the compiler correctly partitions execution steps into
    pre-trial (deterministic) and per-trial (stochastic) phases.
    """
    last_var = script_body.strip().split("\n")[-1].split("=")[0].replace("let", "").strip()
    script = f"@iterations=1\n@output={last_var}\n{script_body}"

    recipe = compile_valuascript(script)
    assert recipe is not None, "Compilation failed unexpectedly"

    # In the new bytecode, we verify by looking up the names from the indices
    registry = recipe["variable_registry"]
    actual_pre_trial_names = {registry[step["result_index"]] for step in recipe["pre_trial_steps"]}
    actual_per_trial_names = {registry[step["result_index"]] for step in recipe["per_trial_steps"]}

    assert set(actual_pre_trial_names) == set(expected_pre_trial_names)
    assert set(actual_per_trial_names) == set(expected_per_trial_names)


# ==============================================================================
# TESTS FOR DEAD CODE ELIMINATION
# ==============================================================================


@pytest.mark.parametrize(
    "script_body, output_var, expected_remaining_vars",
    [
        pytest.param("let x = 10\nlet y = 20", "y", {"y"}, id="basic_elimination"),
        pytest.param("let x = 10\nlet y = x + 5\nlet z = 100", "y", {"x", "y"}, id="eliminates_unrelated_var"),
        pytest.param("let a = 1\nlet b = 2\nlet c = 3\nlet d = a + b", "d", {"a", "b", "d"}, id="multiple_unused_vars"),
    ],
)
def test_dead_code_elimination(script_body, output_var, expected_remaining_vars):
    """
    Validates that the compiler correctly identifies and removes "dead code"
    when the --optimize flag is active.
    """
    script = f"@iterations=1\n@output={output_var}\n{script_body}"
    recipe = compile_valuascript(script, optimize=True)
    assert recipe is not None, "Compilation failed unexpectedly"

    # The variable_registry should now only contain the live variables.
    actual_remaining_vars = set(recipe["variable_registry"])
    assert actual_remaining_vars == expected_remaining_vars


def test_dead_code_elimination_is_disabled_by_default():
    """
    Ensures that if the `optimize` flag is false, no code is eliminated.
    """
    script = "@iterations=1\n@output=live\nlet live = 1\nlet dead = 2"
    recipe = compile_valuascript(script, optimize=False)
    assert recipe is not None
    # All variables should be present in the registry
    assert set(recipe["variable_registry"]) == {"live", "dead"}


# ==============================================================================
# TESTS FOR PREVIEW MODE (LIVE VARIABLE INSPECTION)
# ==============================================================================


@pytest.mark.parametrize(
    "script_body, preview_var, expected_output_var_name, expected_num_trials, expected_remaining_vars",
    [
        pytest.param("let a = 10\nlet b = 20", "a", "a", 1, {"a"}, id="preview_deterministic"),
        pytest.param("let sto = Normal(1,1)\nlet det = 20", "sto", "sto", 100, {"sto"}, id="preview_stochastic"),
        pytest.param("@iterations=9999\nlet a = 10\nlet b = a + 5", "b", "b", 1, {"a", "b"}, id="preview_overrides_iterations"),
    ],
)
def test_preview_mode_compilation(script_body, preview_var, expected_output_var_name, expected_num_trials, expected_remaining_vars):
    """
    Validates that the compiler in `preview_variable` mode correctly:
    1. Overrides the script's directives.
    2. Forces dead code elimination.
    3. Sets the correct number of trials.
    """
    full_script = f"@iterations=999\n@output=ignored\n{script_body}"
    recipe = compile_valuascript(full_script, preview_variable=preview_var)
    assert recipe is not None, "Compilation failed unexpectedly in preview mode"

    # 1. Check that the output variable index points to the correct variable name
    registry = recipe["variable_registry"]
    output_index = recipe["output_variable_index"]
    assert registry[output_index] == expected_output_var_name

    # 2. Check that the number of trials was correctly overridden
    assert recipe["simulation_config"]["num_trials"] == expected_num_trials

    # 3. Check that dead code was correctly eliminated (by checking the registry)
    assert set(registry) == expected_remaining_vars


def test_preview_mode_throws_on_undefined_variable():
    script = "@iterations=1\n@output=a\nlet a = 1"
    with pytest.raises(ValuaScriptError, match="The final @output variable 'undefined_var' is not defined."):
        compile_valuascript(script, preview_variable="undefined_var")