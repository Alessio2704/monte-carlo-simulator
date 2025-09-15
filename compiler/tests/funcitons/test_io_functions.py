import pytest
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode
from vsc.functions import FUNCTION_SIGNATURES

BASE_SCRIPT = "@iterations=1\n@output=result\n"


def get_io_arity_test_cases():
    """Generates test cases for all non-variadic I/O functions."""
    io_functions = {"read_csv_scalar", "read_csv_vector"}
    for func, sig in FUNCTION_SIGNATURES.items():
        if func not in io_functions or sig.get("variadic", False):
            continue
        expected_argc = len(sig["arg_types"])
        if expected_argc > 0:
            yield pytest.param(func, expected_argc - 1, id=f"{func}-too_few")
        yield pytest.param(func, expected_argc + 1, id=f"{func}-too_many")


@pytest.mark.parametrize("func, provided_argc", get_io_arity_test_cases())
def test_io_function_arities(func, provided_argc):
    """
    Validates that I/O built-in functions correctly report argument count mismatches.
    """
    # I/O functions expect string literals, so we must provide them to avoid type errors.
    args_list = ['"test"' for _ in range(provided_argc)]
    args = ", ".join(args_list) if provided_argc > 0 else ""
    script = BASE_SCRIPT + f"let result = {func}({args})"

    # Note: These tests will fail on type errors if not run from a file context,
    # but for arity, the argument count check happens first.
    # We pass a dummy file_path to allow the check to proceed.
    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(script, file_path="dummy.vs")
    assert e.value.code == ErrorCode.ARGUMENT_COUNT_MISMATCH
