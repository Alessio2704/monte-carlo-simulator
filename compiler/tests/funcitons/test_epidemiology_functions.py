import pytest
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode
from vsc.functions import FUNCTION_SIGNATURES

BASE_SCRIPT = "@iterations=1\n@output=s\n"


def get_scientific_arity_test_cases():
    """Generates arity test cases for scientific functions."""
    scientific_functions = {"SirModel"}
    for func, sig in FUNCTION_SIGNATURES.items():
        if func not in scientific_functions or sig.get("variadic", False):
            continue
        expected_argc = len(sig["arg_types"])
        yield pytest.param(func, expected_argc - 1, id=f"{func}-too_few")
        yield pytest.param(func, expected_argc + 1, id=f"{func}-too_many")


@pytest.mark.parametrize("func, provided_argc", get_scientific_arity_test_cases())
def test_scientific_function_arities(func, provided_argc):
    """
    Validates that the SirModel function correctly reports argument count mismatches.
    """
    args_list = ["1" for _ in range(provided_argc)]
    args = ", ".join(args_list)

    script = BASE_SCRIPT + f"let s, i, r = {func}({args})"

    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script)
    assert e.value.code == ErrorCode.ARGUMENT_COUNT_MISMATCH
