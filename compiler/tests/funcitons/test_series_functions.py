import pytest
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode
from vsc.functions import FUNCTION_SIGNATURES

BASE_SCRIPT = "@iterations=1\n@output=result\n"


def get_series_arity_test_cases():
    """Generates test cases for all non-variadic series functions."""
    series_functions = {"sum_series", "series_delta", "npv", "compound_series", "get_element", "delete_element", "grow_series", "interpolate_series", "capitalize_expense"}
    for func, sig in FUNCTION_SIGNATURES.items():
        if func not in series_functions or sig.get("variadic", False):
            continue
        expected_argc = len(sig["arg_types"])
        if expected_argc > 0:
            yield pytest.param(func, expected_argc - 1, id=f"{func}-too_few")
        yield pytest.param(func, expected_argc + 1, id=f"{func}-too_many")


@pytest.mark.parametrize("func, provided_argc", get_series_arity_test_cases())
def test_series_function_arities(func, provided_argc):
    """
    Validates that series built-in functions correctly report argument count mismatches.
    """
    args_list = ["1" for _ in range(provided_argc)]
    args = ", ".join(args_list) if provided_argc > 0 else ""
    script = BASE_SCRIPT + f"let result = {func}({args})"

    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.ARGUMENT_COUNT_MISMATCH
