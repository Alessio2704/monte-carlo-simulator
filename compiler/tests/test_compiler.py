import pytest
from lark import Lark, ParseError
import sys
import os

# This is a bit of a hack to allow the test file to import 'vsc.py'
# from its parent directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now we can import the components from your compiler script
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


# --- Test 1: The "Happy Path" ---
# Use parametrize to test multiple valid scripts with one function
@pytest.mark.parametrize(
    "script, expected_result",
    [
        # Test case 1: Simple literal and identity
        (
            """@iterations=1\nlet a=10\nlet b=a\n@output=b\n""",
            {
                "simulation_config": {"num_trials": 1},
                "execution_steps": [{"type": "literal_assignment", "result": "a", "value": 10.0}, {"type": "execution_assignment", "result": "b", "function": "identity", "args": ["a"]}],
                "output_variable": "b",
            },
        ),
        # Test case 2: Infix expression with precedence
        (
            """@iterations=1\nlet a=2\nlet b=3\nlet c=a+b*5\n@output=c\n""",
            {
                "simulation_config": {"num_trials": 1},
                "execution_steps": [
                    {"type": "literal_assignment", "result": "a", "value": 2.0},
                    {"type": "literal_assignment", "result": "b", "value": 3.0},
                    {"type": "execution_assignment", "result": "c", "function": "add", "args": ["a", {"function": "multiply", "args": ["b", 5.0]}]},
                ],
                "output_variable": "c",
            },
        ),
    ],
)
def test_valid_script_compilation(transformer, script, expected_result):
    """Tests that valid ValuaScript code transforms into the correct dictionary."""
    parse_tree = lark_parser.parse(script)
    result = transformer.transform(parse_tree)
    # We don't check the line/column numbers here as they will be added later
    for step in result["execution_steps"]:
        step.pop("line", None)
    assert result == expected_result


# --- Test 2: Syntax Errors ---
def test_syntax_error_handling():
    """Tests that the Lark parser raises an error for invalid syntax."""
    invalid_script = "@iterations=1\nlet a = [1, 2, 3"  # Missing closing bracket
    with pytest.raises(ParseError):
        lark_parser.parse(invalid_script)


# --- Test 3: Semantic Errors ---
@pytest.mark.parametrize(
    "script, error_message",
    [
        ("@iterations=1\nlet y = x\n@output=y\n", "Variable 'x' used in the calculation for 'y' is not defined before its use."),
        ("@iterations=1\nlet y = unknown_function(10)\n@output=y\n", "Unknown function 'unknown_function' in assignment for 'y'."),
        ("@iterations=1\nlet x = 10\nlet x=20\n@output=x\n", "Variable 'x' is defined more than once."),
        ("@iterations=1\nlet x=10\n@output=z\n", "The output variable 'z' is not defined."),
    ],
)
def test_semantic_error_handling(transformer, script, error_message):
    """Tests that the validate_recipe function catches logical errors."""
    parse_tree = lark_parser.parse(script)
    recipe = transformer.transform(parse_tree)

    with pytest.raises(ValueError, match=error_message):
        validate_recipe(recipe)
