import pytest
from lark import Lark, ParseError
import sys
import os

# Allow the test file to import 'vsc.py' from its parent directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import components from the compiler script
from vsc import ValuaScriptTransformer, validate_recipe

# Load the grammar once for all tests
grammar_path = os.path.join(os.path.dirname(__file__), "..", "valuascript.lark")
with open(grammar_path, "r") as f:
    valuascript_grammar = f.read()

lark_parser = Lark(valuascript_grammar, start="start", parser="lalr")


@pytest.fixture
def transformer():
    """A pytest fixture to provide a fresh transformer for each test."""
    return ValuaScriptTransformer()


# =============================================================================
# --- Test Suite 1: Valid Script Compilation ("Happy Path") ---
# =============================================================================
@pytest.mark.parametrize(
    "description, script_body, expected_steps",
    [
        # --- Basic Assignments ---
        (
            "Scalar literal assignment",
            "let a = 123.45",
            [{"type": "literal_assignment", "result": "a", "value": 123.45}],
        ),
        (
            "Vector literal assignment",
            "let a = [1, 2.5, -3]",
            [{"type": "literal_assignment", "result": "a", "value": [1.0, 2.5, -3.0]}],
        ),
        (
            "Variable-to-variable assignment",
            "let a = 10\nlet b = a",
            [
                {"type": "literal_assignment", "result": "a", "value": 10.0},
                {"type": "execution_assignment", "result": "b", "function": "identity", "args": ["a"]},
            ],
        ),
        # --- Vector Edge Cases ---
        (
            "Empty vector literal",
            "let a = []",
            [{"type": "literal_assignment", "result": "a", "value": []}],
        ),
        (
            "Single element vector literal",
            "let a = [42]",
            [{"type": "literal_assignment", "result": "a", "value": [42.0]}],
        ),
        (
            "Vector as a direct function argument",
            "let x = sum_series([10, 20, 30])",
            [{"type": "execution_assignment", "result": "x", "function": "sum_series", "args": [[10.0, 20.0, 30.0]]}],
        ),
        # --- Infix Operators ---
        (
            "Simple addition",
            "let c = 10 + 20",
            [{"type": "execution_assignment", "result": "c", "function": "add", "args": [10.0, 20.0]}],
        ),
        (
            "Chained addition (flattened)",
            "let c = 10 + 20 + 30",
            [{"type": "execution_assignment", "result": "c", "function": "add", "args": [10.0, 20.0, 30.0]}],
        ),
        (
            "Simple subtraction (nested)",
            "let c = 100 - 10",
            [{"type": "execution_assignment", "result": "c", "function": "subtract", "args": [100.0, 10.0]}],
        ),
        (
            "Chained subtraction (nested)",
            "let c = 100 - 10 - 5",
            [{"type": "execution_assignment", "result": "c", "function": "subtract", "args": [{"function": "subtract", "args": [100.0, 10.0]}, 5.0]}],
        ),
        (
            "Chained multiplication (flattened)",
            "let c = 5 * 4 * 2",
            [{"type": "execution_assignment", "result": "c", "function": "multiply", "args": [5.0, 4.0, 2.0]}],
        ),
        (
            "Chained division (nested)",
            "let c = 100 / 5 / 2",
            [{"type": "execution_assignment", "result": "c", "function": "divide", "args": [{"function": "divide", "args": [100.0, 5.0]}, 2.0]}],
        ),
        (
            "Power/Exponentiation",
            "let c = 2 ^ 8",
            [{"type": "execution_assignment", "result": "c", "function": "power", "args": [2.0, 8.0]}],
        ),
        # --- Complex Expression & Precedence Tests ---
        (
            "Operator precedence (PEMDAS)",
            "let c = 2 + 3 * 4",
            [{"type": "execution_assignment", "result": "c", "function": "add", "args": [2.0, {"function": "multiply", "args": [3.0, 4.0]}]}],
        ),
        (
            "Parentheses to override precedence",
            "let c = (2 + 3) * 4",
            [{"type": "execution_assignment", "result": "c", "function": "multiply", "args": [{"function": "add", "args": [2.0, 3.0]}, 4.0]}],
        ),
        (
            "Mixed addition and subtraction (left associative)",
            "let c = 100 - 20 + 5",
            [{"type": "execution_assignment", "result": "c", "function": "add", "args": [{"function": "subtract", "args": [100.0, 20.0]}, 5.0]}],
        ),
        (
            "Multiple levels of precedence",
            "let c = 2 * 3 + 4 ^ 2",  # 6 + 16
            [{"type": "execution_assignment", "result": "c", "function": "add", "args": [{"function": "multiply", "args": [2.0, 3.0]}, {"function": "power", "args": [4.0, 2.0]}]}],
        ),
        (
            "Multiple parentheses",
            "let c = (2 * (3 + 4)) / 2",  # (2 * 7) / 2
            [{"type": "execution_assignment", "result": "c", "function": "divide", "args": [{"function": "multiply", "args": [2.0, {"function": "add", "args": [3.0, 4.0]}]}, 2.0]}],
        ),
        # --- Distribution Samplers ---
        (
            "Normal distribution",
            "let x = Normal(100, 15)",
            [{"type": "execution_assignment", "result": "x", "function": "Normal", "args": [100.0, 15.0]}],
        ),
        (
            "Pert distribution with variables",
            "let min=8\nlet mode=10\nlet max=15\nlet x=Pert(min,mode,max)",
            [
                {"type": "literal_assignment", "result": "min", "value": 8.0},
                {"type": "literal_assignment", "result": "mode", "value": 10.0},
                {"type": "literal_assignment", "result": "max", "value": 15.0},
                {"type": "execution_assignment", "result": "x", "function": "Pert", "args": ["min", "mode", "max"]},
            ],
        ),
        # --- All Other Built-in Functions ---
        (
            "log function",
            "let x = log(10)",
            [{"type": "execution_assignment", "result": "x", "function": "log", "args": [10.0]}],
        ),
        (
            "get_element function",
            "let x = [1,2,3]\nlet y = get_element(x, -1)",
            [
                {"type": "literal_assignment", "result": "x", "value": [1.0, 2.0, 3.0]},
                {"type": "execution_assignment", "result": "y", "function": "get_element", "args": ["x", -1.0]},
            ],
        ),
        (
            "compose_vector function",
            "let a=1\nlet b=2\nlet c=compose_vector(a, b, 3)",
            [
                {"type": "literal_assignment", "result": "a", "value": 1.0},
                {"type": "literal_assignment", "result": "b", "value": 2.0},
                {"type": "execution_assignment", "result": "c", "function": "compose_vector", "args": ["a", "b", 3.0]},
            ],
        ),
        (
            "npv with nested expression",
            "let cfs=[100]\nlet wacc=0.1\nlet x = npv(cfs, wacc*1.1)",
            [
                {"type": "literal_assignment", "result": "cfs", "value": [100.0]},
                {"type": "literal_assignment", "result": "wacc", "value": 0.1},
                {"type": "execution_assignment", "result": "x", "function": "npv", "args": ["cfs", {"function": "multiply", "args": ["wacc", 1.1]}]},
            ],
        ),
    ],
)
def test_valid_script_compilation(transformer, description, script_body, expected_steps):
    """Tests that valid ValuaScript code transforms into the correct dictionary."""
    output_var = expected_steps[-1]["result"]
    full_script = f"@iterations=1\n{script_body}\n@output={output_var}"

    expected_result = {
        "simulation_config": {"num_trials": 1},
        "execution_steps": expected_steps,
        "output_variable": output_var,
    }

    parse_tree = lark_parser.parse(full_script)
    result = transformer.transform(parse_tree)

    assert result == expected_result, f"Test failed for: {description}"


# =============================================================================
# --- Test Suite 2: Syntax Error Handling ---
# =============================================================================
@pytest.mark.parametrize(
    "description, invalid_script_body",
    [
        ("Missing closing bracket", "let a = [1, 2, 3"),
        ("Invalid let statement", "let a = b c"),
        ("Unmatched parenthesis", "let a = (2 + 3 * 4"),
        ("Missing operator", "let a = 2 3"),
        ("Missing output variable name", "let a=1\n@output="),
    ],
)
def test_syntax_error_handling(description, invalid_script_body):
    """Tests that the Lark parser raises an error for invalid syntax."""
    full_script = f"@iterations=1\n{invalid_script_body}"
    with pytest.raises(ParseError):
        lark_parser.parse(full_script)


# =============================================================================
# --- Test Suite 3: Semantic Error Handling ---
# =============================================================================
@pytest.mark.parametrize(
    "description, script_body, error_message",
    [
        ("Using undefined variable", "let y = x\n@output=y", "Variable 'x' used in the calculation for 'y' is not defined before its use."),
        ("Using unknown function", "let y = unknown_function(10)\n@output=y", "Unknown function 'unknown_function' in assignment for 'y'."),
        ("Duplicate variable definition", "let x = 10\nlet x=20\n@output=x", "Variable 'x' is defined more than once."),
        ("Undefined output variable", "let x=10\n@output=z", "The output variable 'z' is not defined."),
        ("No output variable specified", "let x=10", "An @output variable must be specified."),
    ],
)
def test_semantic_error_handling(transformer, description, script_body, error_message):
    """Tests that the validate_recipe function catches logical errors."""

    if description == "No output variable specified":
        # To specifically test the validator's check for an empty output_variable,
        # we bypass the parser (which would fail) and create the faulty recipe manually.
        recipe = {"simulation_config": {"num_trials": 1}, "execution_steps": [{"type": "literal_assignment", "result": "x", "value": 10.0}], "output_variable": ""}  # The semantic error
    else:
        # For all other semantic tests, the script body is syntactically valid.
        full_script = f"@iterations=1\n{script_body}"
        parse_tree = lark_parser.parse(full_script)
        recipe = transformer.transform(parse_tree)

    with pytest.raises(ValueError, match=error_message):
        validate_recipe(recipe)
