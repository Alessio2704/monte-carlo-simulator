import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lark.exceptions import UnexpectedToken, UnexpectedInput, UnexpectedCharacters
from vsc.compiler import validate_valuascript
from vsc.exceptions import ValuaScriptError
from vsc.config import FUNCTION_SIGNATURES


@pytest.fixture
def base_script():
    return "@iterations = 100\n@output = result\n"


def test_valid_scripts_compile_successfully():
    validate_valuascript("@iterations=1\n@output=x\nlet x = 1")
    validate_valuascript("@iterations=1\n@output=y\nlet x=1\nlet y=x")
    validate_valuascript(
        """
        @iterations=100
        @output=pres_val
        let cf = grow_series(100, 0.1, 5)
        let rate = 0.08
        let pres_val = npv(rate, cf)
        """
    )
    validate_valuascript("@iterations=1\n@output=x\nlet x = sum_series(grow_series(1, 1, 1))")
    validate_valuascript('@iterations=1\n@output=x\n@output_file="f.csv"\nlet x = 1')
    validate_valuascript("@iterations=1\n@output=v\nlet my_vec = [1,2,3]\nlet v = delete_element(my_vec, 1)")
    validate_valuascript("@iterations=1\n@output=x\nlet my_vec=[100,200]\nlet x = my_vec[0]")
    validate_valuascript("@iterations=1\n@output=x\nlet my_vec=[100,200]\nlet i=1\nlet x = my_vec[i]")
    validate_valuascript("@iterations=1\n@output=x\nlet my_vec=[100,200]\nlet x = my_vec[1-1]")
    validate_valuascript("@iterations=1\n@output=x\nlet my_vec=[1,2,3]\nlet x = my_vec[:-1]")
    validate_valuascript("@iterations=1\n@output=x\nlet x = 1_000_000")
    validate_valuascript("@iterations=1\n@output=x\nlet x = 1_234.567_8")
    validate_valuascript("@iterations=1\n@output=x\nlet x = -5_000")

    script = """
    # This is a test model
    @iterations = 100
    @output     = final_value
    let initial = 10
    let rate    = 0.5
    let final_value = initial * (1 + rate)
    """
    assert validate_valuascript(script) is not None


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
        validate_valuascript(script)


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
        validate_valuascript(script_body)


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
        validate_valuascript(script_body)


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
        validate_valuascript(script)


# ==============================================================================
# TESTS FOR LOOP-INVARIANT CODE MOTION OPTIMIZATION
# ==============================================================================


@pytest.mark.parametrize(
    "script_body, expected_pre_trial, expected_per_trial",
    [
        pytest.param("let x = 10\nlet y = x + 5", ["x", "y"], [], id="all_deterministic"),
        pytest.param("let x = Normal(1,1)\nlet y = Pert(1,2,3)", [], ["x", "y"], id="all_stochastic"),
        pytest.param("let x = 100\nlet y = Normal(x, 10)", ["x"], ["y"], id="deterministic_feeds_stochastic"),
        pytest.param("let x = Normal(1,1)\nlet y = x + 10\nlet z = y * 2", [], ["x", "y", "z"], id="stochastic_taints_chain"),
        pytest.param("let result = 10 + Normal(1, 0.1)", [], ["result"], id="bugfix_nested_stochastic_in_expr"),
        pytest.param("let x = 10\nlet y = log(x)\nlet z = Normal(y, 1)", ["x", "y"], ["z"], id="deterministic_chain_feeds_stochastic"),
        pytest.param("let sto = Normal(1,1)\nlet result = log(sto)", [], ["sto", "result"], id="deterministic_func_with_stochastic_arg"),
        pytest.param("let a = Normal(1,1)\nlet b = Normal(2,2)\nlet c = a + b", [], ["a", "b", "c"], id="expr_with_multiple_stochastic_vars"),
        pytest.param(
            """
            let sto = Normal(1,1)
            let det = 100
            let result = sto + det
            """,
            ["det"],
            ["sto", "result"],
            id="simple_mix_with_dependency",
        ),
        pytest.param("let unused_sto = Normal(1,1)\nlet result = 10", ["result"], ["unused_sto"], id="unused_stochastic_variable"),
        pytest.param("let unused_det = 100\nlet result = Normal(1,1)", ["unused_det"], ["result"], id="unused_deterministic_variable"),
        pytest.param(
            """
            let det1 = 10
            let det2 = 20
            let sto1 = Normal(1, 1)
            let det3 = det1 + det2
            let sto2 = sto1 + det1
            let sto3 = Pert(1, det3, 3)
            let result = sto2 + sto3
            """,
            ["det1", "det2", "det3"],
            ["sto1", "sto2", "sto3", "result"],
            id="complex_mixed_dependency_graph",
        ),
        pytest.param(
            # Data loading functions are deterministic and should always be pre-trial
            'let data = read_csv_vector("p.csv", "c")',
            ["data"],
            [],
            id="data_loading_is_always_pre_trial",
        ),
        pytest.param(
            """
            let historical_data = [1,2,3]
            let mean_val = historical_data[0]
            let result = Normal(mean_val, 1)
            """,
            ["historical_data", "mean_val"],
            ["result"],
            id="pre_trial_vector_access_feeds_stochastic",
        ),
    ],
)
def test_optimization_step_partitioning(script_body, expected_pre_trial, expected_per_trial):
    """
    Validates that the compiler correctly partitions execution steps into
    pre-trial (deterministic) and per-trial (stochastic) phases.
    """
    # We must have a valid output variable, even if it's not the main focus of the test.
    # We choose the last defined variable as the output for simplicity.
    last_var = script_body.strip().split("\n")[-1].split("=")[0].replace("let", "").strip()
    script = f"@iterations=1\n@output={last_var}\n{script_body}"

    recipe = validate_valuascript(script)
    assert recipe is not None, "Compilation failed unexpectedly"

    actual_pre_trial_vars = [step["result"] for step in recipe["pre_trial_steps"]]
    actual_per_trial_vars = [step["result"] for step in recipe["per_trial_steps"]]

    assert set(actual_pre_trial_vars) == set(expected_pre_trial)
    assert set(actual_per_trial_vars) == set(expected_per_trial)