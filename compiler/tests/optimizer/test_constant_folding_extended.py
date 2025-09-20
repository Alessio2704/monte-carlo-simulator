import pytest
from pathlib import Path
from textwrap import dedent

# Import the full pipeline helper from the other test file
from .test_constant_folding import run_full_pipeline_to_optimized_ir, create_dummy_file

# --- 1. Tests for Variadic (Multi-Argument) Functions ---


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
        ("sin(0)", 0.0),
        ("cos(0)", 1.0),
        ("tan(0)", 0.0),
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
