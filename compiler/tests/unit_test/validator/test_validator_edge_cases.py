import pytest
from pathlib import Path

from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.exceptions import ValuaScriptError, ErrorCode


# --- Helper to create dummy files for testing imports ---
def create_dummy_file(directory, filename, content):
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)


# --- Helper for testing expected failures ---
def run_validation_with_error(script_content: str, file_path: str, expected_code: ErrorCode):
    """Asserts that the validation phase raises a specific ValuaScriptError."""
    with pytest.raises(ValuaScriptError) as excinfo:
        ast = parse_valuascript(script_content)
        symbol_table = discover_symbols(ast, file_path)
        enriched_table = infer_types_and_taint(symbol_table)
        validate_semantics(enriched_table)
    assert excinfo.value.code == expected_code


# --- 1. Arity Mismatch Tests (User-Defined Functions) ---


def test_udf_call_too_many_arguments(tmp_path):
    script = """
    @iterations=1
    @output=x
    func my_func(a: scalar) -> scalar { return a }
    let x = my_func(1, 2)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.ARGUMENT_COUNT_MISMATCH)


def test_udf_call_too_few_arguments(tmp_path):
    script = """
    @iterations=1
    @output=x
    func my_func(a: scalar, b: scalar) -> scalar { return a }
    let x = my_func(1)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.ARGUMENT_COUNT_MISMATCH)


def test_udf_call_zero_arg_with_argument(tmp_path):
    script = """
    @iterations=1
    @output=x
    func my_func() -> scalar { return 1 }
    let x = my_func(123)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.ARGUMENT_COUNT_MISMATCH)


def test_multi_assignment_arity_mismatch(tmp_path):
    script = """
    @iterations=1
    @output=x
    func my_func() -> (scalar) { return (1, 2) }
    let x = my_func()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    # This is a type mismatch: assigning a tuple to a single variable.
    run_validation_with_error(script, file_path, ErrorCode.RETURN_TYPE_MISMATCH)


# --- 2. Operator Type Mismatches ---


def test_non_scalar_comparison(tmp_path):
    script = """
    @iterations=1
    @output=x
    let x = [1] > [2]
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    # The '>' operator is the '__gt__' function which expects scalars.
    run_validation_with_error(script, file_path, ErrorCode.ARGUMENT_TYPE_MISMATCH)


def test_non_boolean_logical_operator(tmp_path):
    script = """
    @iterations=1
    @output=x
    let x = 1 and true
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    # The 'and' operator is the '__and__' function which expects booleans.
    run_validation_with_error(script, file_path, ErrorCode.ARGUMENT_TYPE_MISMATCH)


@pytest.mark.parametrize("expression", ['1 + "a"', '"a" - 1', "1 * true", "false / 1", '2 ^ "a"'])
def test_mathematical_operator_with_non_numeric_type(tmp_path, expression):
    """
    This is a regression test for the bug where the validator failed to check
    argument types for mathematical operators.
    """
    script = f"""
    @iterations=1
    @output=x
    let x = {expression}
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.OPERATOR_TYPE_MISMATCH)


# --- 3. Structural and Scope Edge Cases ---


def test_function_missing_return_statement(tmp_path):
    script = """
    @iterations=1
    @output=x
    func my_func() -> scalar { 
        let y = 1 
    }
    let x = my_func()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.MISSING_RETURN_STATEMENT)


@pytest.mark.parametrize("content", ["", "# A file with only a comment"])
def test_empty_and_comment_only_files(tmp_path, content):
    file_path = create_dummy_file(tmp_path, "main.vs", content)
    # An empty file is a valid script that is simply missing required directives.
    run_validation_with_error(content, file_path, ErrorCode.MISSING_ITERATIONS_DIRECTIVE)


# --- 4. Advanced Module and Import Edge Cases ---


def test_importing_a_non_module_file(tmp_path):
    non_module_content = "let x = 1 # This script is missing @module"
    main_content = '@import "not_a_module.vs"\n@iterations=1\n@output=y\nlet y=1'

    create_dummy_file(tmp_path, "not_a_module.vs", non_module_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)

    run_validation_with_error(main_content, main_path, ErrorCode.IMPORT_NOT_A_MODULE)


def test_module_with_disallowed_directive(tmp_path):
    # We compile the module file directly to test its own rules.
    script = """
    @module
    @output = x  # Not allowed in a module
    """
    file_path = create_dummy_file(tmp_path, "module.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE)
