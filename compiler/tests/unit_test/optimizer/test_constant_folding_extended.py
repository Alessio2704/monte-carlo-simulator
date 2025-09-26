import pytest
from pathlib import Path
from textwrap import dedent
from vsc.optimizer.constant_folding import run_constant_folding
from vsc.parser.parser import _StringLiteral
from vsc.optimizer.ir_validator import IRValidator, IRValidationError

# Import the full pipeline helper from the other test file
from .test_constant_folding import run_full_pipeline_to_optimized_ir, create_dummy_file

# --- 1. Tests for Variadic (Multi-Argument) Functions ---


def run_constant_folding_and_validate(input_ir: str) -> list:

    try:
        IRValidator(input_ir).validate()

        final_ir = run_constant_folding(input_ir)
        IRValidator(final_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"An optimization phase produced an invalid IR: {e}")

    return final_ir


def test_folds_variadic_add(tmp_path):
    """Tests that add(1, 2, 3, 4) is correctly folded."""
    script = "@output=x\n@iterations=1\nlet x = 1 + 2 + 3 + 4"  # Expected: 10
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)
    assert optimized_ir[0]["value"] == 10


def test_folds_variadic_multiply(tmp_path):
    """Tests that multiply(2, 3, 4) is correctly folded."""
    script = "@output=x\n@iterations=1\nlet x = 2 * 3 * 4"  # Expected: 24
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)
    assert optimized_ir[0]["value"] == 24


def test_folds_variadic_logical_and(tmp_path):
    script = "@output=x\n@iterations=1\nlet x = true and true and false"  # Expected: false
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)
    assert optimized_ir[0]["value"] is False


def test_folds_variadic_logical_or(tmp_path):
    script = "@output=x\n@iterations=1\nlet x = false or false or true"  # Expected: true
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)
    assert optimized_ir[0]["value"] is True


def test_folds_variadic_logical_and_or(tmp_path):
    script = "@iterations = 10000\nlet a = true and false and true or false\n@output = a"  # Expected: false
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)
    assert optimized_ir[0]["value"] is False


# --- 2. Tests for All Mathematical and Logical Functions ---


@pytest.mark.parametrize(
    "expression, expected_value",
    [
        # Mathematical
        ("10 - 3", 7),
        ("20 / 4", 5.0),
        ("2 ^ 10", 1024),
        ("log(1)", 0.0),
        ("log10(100)", 2.0),
        ("exp(0)", 1.0),
        ("[1,2,3] + [4,5,6]", [5, 7, 9]),
        ("14 + [4,5,6]", [18, 19, 20]),
        ("[42,51,62] + 11", [53, 62, 73]),
        ("[1,2,3] - [4,5,6]", [-3, -3, -3]),
        ("14 - [4,5,6]", [10, 9, 8]),
        ("[42,51,62] - 11", [31, 40, 51]),
        ("[1,2,3] * [4,5,6]", [4, 10, 18]),
        ("[50, 70, 80] / 2", [25, 35, 40]),
        ("([50, 70, 80] + [2, 2, 2]) / 2", [26, 36, 41]),
        # Comparison
        ("100 > 50", True),
        ("100 < 50", False),
        ("50 >= 50", True),
        ("50 <= 49", False),
        ("50 == 50", True),
        ("50 != 51", True),
        # Logical
        ("not true", False),
        ("true and false", False),
        ("true or false", True),
    ],
)
def test_all_core_functions_fold_correctly(tmp_path, expression, expected_value):
    script = f"@output=x\n@iterations=1\nlet x = {expression}"
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    assert optimized_ir[0]["type"] == "literal_assignment"

    # Use pytest.approx for floating point comparisons
    if isinstance(expected_value, float):
        assert optimized_ir[0]["value"] == pytest.approx(expected_value)
    else:
        assert optimized_ir[0]["value"] == expected_value


# --- 3. Safety and Edge Case Tests ---


def test_does_not_fold_with_invalid_math_domain(tmp_path):
    """Ensures log(-1) is not folded and does not crash the compiler."""
    script = "@output=x\n@iterations=1\nlet x = log(-1)"
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # We expect the semantic validator to fail this, but if it didn't,
    # the folder must not crash. We can't use the full pipeline here.
    from vsc.ir_generator import generate_ir
    from vsc.optimizer.constant_folding import run_constant_folding

    # Bypass semantic validation for this specific test
    ast = dedent(script).strip()
    # A fake model is needed
    fake_model = {
        "processed_asts": {file_path: {"execution_steps": [{"type": "execution_assignment", "result": "x", "function": "log", "args": [-1], "line": 3}]}},
        "main_file_path": file_path,
        "user_defined_functions": {},
    }
    initial_ir = generate_ir(fake_model)

    # Run only the constant folding pass
    final_ir = run_constant_folding(initial_ir)

    # The instruction should remain unchanged
    assert final_ir[0]["function"] == "log"
    assert final_ir[0]["args"] == [-1]


def test_nested_function_folding(tmp_path):
    """Tests that functions nested inside other functions are folded first."""
    script = "@output=x\n@iterations=1\nlet x = 10 * (5 + (20 / 10))"  # 10 * (5 + 2) = 70
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    assert optimized_ir[0]["value"] == 70.0


def test_handles_string_literal_without_looping():
    """
    Regression test for the infinite loop bug.

    The bug occurred when the constant folder's deepcopy created new
    _StringLiteral objects, causing the fixed-point comparison to always
    fail. This test passes an IR with a _StringLiteral that should not be
    changed. The test passes if the optimizer correctly terminates (i.e.,
    doesn't loop infinitely) and returns the identical IR.
    """
    input_ir = [{"type": "literal_assignment", "result": ["my_str"], "value": _StringLiteral("hello")}]

    # This call would hang indefinitely before the fix
    result_ir = run_constant_folding_and_validate(input_ir)

    assert result_ir == input_ir


def test_folds_basic_math_operations():
    """Tests that simple math expressions with literals are folded."""
    input_ir = [
        {"type": "execution_assignment", "result": ["x"], "function": "add", "args": [5, 10]},
        {"type": "execution_assignment", "result": ["y"], "function": "multiply", "args": [2, 3, 4]},
    ]
    expected_ir = [
        {"type": "literal_assignment", "result": ["x"], "value": 15.0, "line": -1},
        {"type": "literal_assignment", "result": ["y"], "value": 24.0, "line": -1},
    ]
    result_ir = run_constant_folding_and_validate(input_ir)
    assert result_ir == expected_ir


def test_propagates_constants_and_folds():
    """Tests that the optimizer propagates a constant and then folds a subsequent expression."""
    input_ir = [
        {"type": "literal_assignment", "result": ["a"], "value": 10},
        {"type": "execution_assignment", "result": ["b"], "function": "subtract", "args": ["a", 3]},
    ]
    expected_ir = [
        {"type": "literal_assignment", "result": ["a"], "value": 10},
        {"type": "literal_assignment", "result": ["b"], "value": 7.0, "line": -1},
    ]
    result_ir = run_constant_folding_and_validate(input_ir)
    assert result_ir == expected_ir


def test_preserves_unfoldable_expressions():
    """Ensures that expressions involving variables are not changed."""
    input_ir = [
        {"type": "execution_assignment", "result": ["x"], "function": "Normal", "args": [10, 1]},
        {"type": "literal_assignment", "result": ["a"], "value": 10},
        {"type": "execution_assignment", "result": ["b"], "function": "add", "args": ["a", "x"]},
    ]
    # The 'a' should be propagated, but the expression cannot be fully folded.
    expected_ir = [
        {"type": "execution_assignment", "result": ["x"], "function": "Normal", "args": [10, 1]},
        {"type": "literal_assignment", "result": ["a"], "value": 10},
        {"type": "execution_assignment", "result": ["b"], "function": "add", "args": [10, "x"]},
    ]
    result_ir = run_constant_folding_and_validate(input_ir)
    print(result_ir)
    assert result_ir == expected_ir
