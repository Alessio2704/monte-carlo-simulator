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


# --- Helper to run the pipeline up to and including validation ---
def run_validation_pipeline(script_content: str, file_path: str):
    """A pipeline helper that runs the full front-end."""
    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_table = validate_semantics(enriched_table)
    return validated_table


# --- Helper for testing expected failures ---
def run_validation_with_error(script_content: str, file_path: str, expected_code: ErrorCode):
    """Asserts that the validation phase raises a specific ValuaScriptError."""
    with pytest.raises(ValuaScriptError) as excinfo:
        run_validation_pipeline(script_content, file_path)
    assert excinfo.value.code == expected_code


# --- 1. Test "Happy Path" - A valid script should pass ---


def test_valid_script_passes_validation(tmp_path):
    """Ensures a correct and complex script does not raise any errors."""
    script = """
    @iterations = 1000
    @output = result
    func my_add(a: scalar, b: scalar) -> scalar {
        return a + b
    }

    let x = Normal(10, 2)
    let y = 20
    let result = my_add(x, y)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    try:
        run_validation_pipeline(script, file_path)
    except ValuaScriptError as e:
        pytest.fail(f"Validation failed unexpectedly: {e}")


# --- 2. Directive Validation Tests (Rewritten for clarity) ---


def test_catches_missing_iterations(tmp_path):
    script = "@output = x"
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.MISSING_ITERATIONS_DIRECTIVE)


def test_catches_missing_output(tmp_path):
    script = "@iterations = 100"
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.MISSING_OUTPUT_DIRECTIVE)


def test_catches_invalid_directive_type(tmp_path):
    script = '@iterations = "bad"\n@output=x'
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.INVALID_DIRECTIVE_VALUE)


def test_catches_global_let_in_module(tmp_path):
    script_module = """
    @module
    let x = 1 # Not allowed
    """
    module_path = create_dummy_file(tmp_path, "module.vs", script_module)
    script_main = f'@import "{module_path}"\n@iterations=1\n@output=y\nlet y=1'
    main_path = create_dummy_file(tmp_path, "main.vs", script_main)
    # This error is correctly caught during symbol discovery, which is part of the pipeline.
    run_validation_with_error(script_main, main_path, ErrorCode.GLOBAL_LET_IN_MODULE)


# --- 3. Definition, Scope, and Call Validation Tests ---


@pytest.mark.parametrize(
    "script_body, code",
    [
        ("let x = y", ErrorCode.UNDEFINED_VARIABLE),
        ("let x = unknown_func()", ErrorCode.UNKNOWN_FUNCTION),
        ("let x = Normal(1)", ErrorCode.ARGUMENT_COUNT_MISMATCH),
        ("let x = Normal(1, 2, 3)", ErrorCode.ARGUMENT_COUNT_MISMATCH),
    ],
)
def test_catches_definition_and_scope_errors(tmp_path, script_body, code):
    script = f"@iterations=1\n@output=x\n{script_body}"
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, code)


# --- 4. Type Mismatch Validation Tests (Rewritten for clarity) ---


def test_catches_arg_type_mismatch(tmp_path):
    script = '@iterations=1\n@output=x\nlet x = Normal("a", "b")'
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.ARGUMENT_TYPE_MISMATCH)


def test_catches_if_condition_not_boolean(tmp_path):
    script = "@iterations=1\n@output=x\nlet x = if 1 then 10 else 20"
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.IF_CONDITION_NOT_BOOLEAN)


def test_catches_if_else_type_mismatch(tmp_path):
    script = '@iterations=1\n@output=x\nlet x = if true then 10 else "a"'
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.IF_ELSE_TYPE_MISMATCH)


def test_catches_return_type_mismatch(tmp_path):
    script = '@iterations=1\n@output=x\nfunc f() -> scalar { return "a" }\nlet x=f()'
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.RETURN_TYPE_MISMATCH)


def test_catches_multi_return_type_mismatch(tmp_path):
    script = "@iterations=1\n@output=a\nfunc f() -> (scalar, vector) { return ([1], 1) }\nlet a,b=f()"
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.RETURN_TYPE_MISMATCH)


# --- 5. Recursion Validation Tests ---


def test_catches_direct_recursion(tmp_path):
    script = """
    @iterations=1
    @output=x
    func a() -> scalar {
        return a()
    }
    let x = a()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.RECURSIVE_CALL_DETECTED)


def test_catches_mutual_recursion(tmp_path):
    script = """
    @iterations=1
    @output=x
    func a() -> scalar { return b() }
    func b() -> scalar { return a() }
    let x = a()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, ErrorCode.RECURSIVE_CALL_DETECTED)

@pytest.mark.parametrize(
    "vector_literal, expected_error_code",
    [
        ('[1, 2.5, "hello"]', ErrorCode.MIXED_TYPES_IN_VECTOR),
        ("[true, 15]", ErrorCode.MIXED_TYPES_IN_VECTOR),
        ('["a", false]', ErrorCode.MIXED_TYPES_IN_VECTOR),
    ],
    ids=["scalar_and_string", "bool_and_scalar", "string_and_bool"],
)
def test_catches_mixed_types_in_vector_literal(tmp_path, vector_literal, expected_error_code):
    """
    Ensures the validator rejects vector literals containing multiple data types.
    """
    script = f"""
    @iterations=1
    @output=x
    let x = {vector_literal}
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    run_validation_with_error(script, file_path, expected_error_code)
