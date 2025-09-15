import pytest
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode
from vsc.functions import FUNCTION_SIGNATURES

BASE_SCRIPT = "@iterations=1\n@output=result\n"


def get_statistics_arity_test_cases():
    """Generates test cases for all non-variadic statistics (sampler) functions."""
    statistics_functions = {"Normal", "Lognormal", "Beta", "Uniform", "Bernoulli", "Pert", "Triangular"}
    for func, sig in FUNCTION_SIGNATURES.items():
        if func not in statistics_functions or sig.get("variadic", False):
            continue
        expected_argc = len(sig["arg_types"])
        if expected_argc > 0:
            yield pytest.param(func, expected_argc - 1, id=f"{func}-too_few")
        yield pytest.param(func, expected_argc + 1, id=f"{func}-too_many")


@pytest.mark.parametrize("func, provided_argc", get_statistics_arity_test_cases())
def test_statistics_function_arities(func, provided_argc):
    """
    Validates that statistics built-in functions correctly report argument count mismatches.
    """
    args_list = ["1" for _ in range(provided_argc)]
    args = ", ".join(args_list) if provided_argc > 0 else ""
    script = BASE_SCRIPT + f"let result = {func}({args})"

    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.ARGUMENT_COUNT_MISMATCH
