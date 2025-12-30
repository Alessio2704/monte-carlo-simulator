import pytest
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode
from vsc.functions import FUNCTION_SIGNATURES

BASE_SCRIPT = "@iterations=1\n@output=result\n"


def get_financial_arity_test_cases():
    """Generates test cases for all non-variadic financial functions."""
    financial_functions = {"BlackScholes"}
    for func, sig in FUNCTION_SIGNATURES.items():
        if func not in financial_functions or sig.get("variadic", False):
            continue
        expected_argc = len(sig["arg_types"])
        if expected_argc > 0:
            yield pytest.param(func, expected_argc - 1, id=f"{func}-too_few")
        yield pytest.param(func, expected_argc + 1, id=f"{func}-too_many")


@pytest.mark.parametrize("func, provided_argc", get_financial_arity_test_cases())
def test_financial_function_arities(func, provided_argc):
    """
    Validates that financial built-in functions correctly report argument count mismatches.
    """
    arg_types = FUNCTION_SIGNATURES[func]["arg_types"]
    args_list = []

    for i in range(provided_argc):
        expected_type = arg_types[min(i, len(arg_types) - 1)]
        args_list.append(f'"arg"' if expected_type == "string" else "1")

    args = ", ".join(args_list) if provided_argc > 0 else ""
    script = BASE_SCRIPT + f"let result = {func}({args})"

    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.ARGUMENT_COUNT_MISMATCH
