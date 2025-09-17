import pytest
import lark
from vsc.parser import parse_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode

# We can import the Lark exceptions to test for them, although our custom
# pre-parser checks should catch many common errors first.
from lark.exceptions import UnexpectedInput


# --- 1. High-Level Integration Test with a Complex File ---


def test_parses_comprehensive_valuation_script():
    """
    Tests the parser against the large, real-world valuation script provided.
    This acts as a high-level integration test.
    """
    script_content = """
    # -- Alphabet (Google) Valuation August 2025 --

    @import "modules/wacc.vs"
    @import "modules/segment.vs"
    @import "modules/fcff.vs"

    @iterations = 10_000_000

    # -- R&D Capitalization
    let value_of_research_assets, current_year_amortization = get_rd()

    # -- WACC --
    let wacc = get_wacc()

    # -- Revenues study --
    let gcp_market_share = 0.11
    let gcp_target_market_share = Uniform(0.1, 0.15)
    let cloud_market_size = 13624 / gcp_market_share * 4
    let cloud_cagr = Pert(0.15, 0.20, 0.25)
    
    let total_revenues = gcp_revenues + yt_revenues + google_network_revenues
    let total_ebit = gcp_ebit + yt_ebit + google_network_ebit
    
    let ebit_after_tax = total_ebit * (1 - future_tax_rate)
    
    let year_10_growth = total_revenues[-1] / total_revenues[-2] - 1
    
    let value_per_share = (sum_of_d_fcff + d_tv - get_debt() + get_cash()) / get_shares()

    @output = value_per_share
    """

    ast = parse_valuascript(script_content)

    # Assert on the top-level structure
    assert "imports" in ast
    assert "directives" in ast
    assert "execution_steps" in ast
    assert "function_definitions" in ast

    # Assert counts to ensure everything was found
    assert len(ast["imports"]) == 3
    assert len(ast["directives"]) == 2
    assert len(ast["execution_steps"]) == 11
    assert len(ast["function_definitions"]) == 0

    # Spot check a few complex nodes
    multi_assignment = ast["execution_steps"][0]
    assert multi_assignment["type"] == "multi_assignment"
    assert multi_assignment["results"] == ["value_of_research_assets", "current_year_amortization"]
    assert multi_assignment["function"] == "get_rd"

    complex_math = ast["execution_steps"][4]
    assert complex_math["result"] == "cloud_market_size"
    assert complex_math["function"] == "multiply"

    element_access = ast["execution_steps"][8]
    assert element_access["result"] == "ebit_after_tax"
    assert element_access["function"] == "multiply"
    assert len(element_access["args"]) == 2
    assert element_access["args"][1]["function"] == "subtract"
    assert element_access["args"][1]["args"][0] == 1
    assert element_access["args"][1]["args"][1] == "future_tax_rate"


# --- 2. Granular Feature Tests ---


@pytest.mark.parametrize(
    "directive_code, expected_name, expected_value_type",
    [
        ("@iterations = 1000", "iterations", int),
        ("@output = my_var", "output", str),
        ('@output_file = "results.csv"', "output_file", "_StringLiteral"),
        ("@module", "module", bool),
        ('@import "my_module.vs"', "import", str),  # Special import type
    ],
)
def test_directive_parsing(directive_code, expected_name, expected_value_type):
    """Tests that all directive types are parsed correctly."""
    ast = parse_valuascript(directive_code)

    if expected_name == "import":
        item = ast["imports"][0]
        assert item["type"] == "import"
        assert isinstance(item["path"], str)
    else:
        item = ast["directives"][0]
        assert item["name"] == expected_name
        if expected_value_type == "_StringLiteral":
            # Our transformer wraps strings in a custom class
            assert item["value"].__class__.__name__ == expected_value_type
        else:
            assert isinstance(item["value"], expected_value_type)


def test_multi_assignment_parsing():
    """Ensures multi-assignments are captured with a 'results' list."""
    script = "let revenues, ebit, margin = calculate_segment(data)"
    ast = parse_valuascript(script)
    step = ast["execution_steps"][0]
    assert step["type"] == "multi_assignment"
    assert step["results"] == ["revenues", "ebit", "margin"]
    assert step["function"] == "calculate_segment"
    assert len(step["args"]) == 1


def test_operator_precedence_and_nesting():
    """Tests that mathematical expressions respect operator precedence."""
    script = "let result = 2 + 3 * 4 - 5 ^ 2 / 2"  # Expected: 2 + 12 - 25 / 2 = 1.5
    ast = parse_valuascript(script)
    expr = ast["execution_steps"][0]

    # Should be a tree of additions/subtractions at the top level
    assert expr["function"] == "subtract"

    # Left side of subtraction is (2 + (3 * 4))
    add_node = expr["args"][0]
    assert add_node["function"] == "add"
    assert add_node["args"][0] == 2
    assert add_node["args"][1]["function"] == "multiply"
    assert add_node["args"][1]["args"] == [3, 4]

    # Right side of subtraction is ((5 ^ 2) / 2)
    div_node = expr["args"][1]
    assert div_node["function"] == "divide"
    assert div_node["args"][0]["function"] == "power"
    assert div_node["args"][0]["args"] == [5, 2]
    assert div_node["args"][1] == 2


def test_conditional_expression_parsing():
    """Tests if/then/else expressions."""
    script = "let result = if x > 5 then 1 else 0"
    ast = parse_valuascript(script)
    step = ast["execution_steps"][0]

    assert step["type"] == "conditional_expression"
    assert step["result"] == "result"

    # Condition
    condition = step["condition"]
    assert condition["function"] == "__gt__"  # Maps to internal function name
    assert condition["args"][0].value == "x"
    assert condition["args"][1] == 5

    # Branches
    assert step["then_expr"] == 1
    assert step["else_expr"] == 0


def test_logical_and_or_not_expression_parsing():
    """Tests logical operators and their precedence."""
    script = "let result = not a and b or c"  # Expected: ((not a) and b) or c
    ast = parse_valuascript(script)
    step = ast["execution_steps"][0]

    # Top level is 'or'
    assert step["function"] == "__or__"
    assert step["args"][1].value == "c"

    # Left side of 'or' is 'and'
    and_node = step["args"][0]
    assert and_node["function"] == "__and__"
    assert and_node["args"][1].value == "b"

    # Left side of 'and' is 'not'
    not_node = and_node["args"][0]
    assert not_node["function"] == "__not__"
    assert not_node["args"][0].value == "a"


# --- 3. Function Definition Tests ---


def test_full_function_definition_parsing():
    """Tests a complete function definition with all features."""
    script = """
    func calculate_dcf(rate: scalar, cashflows: vector) -> scalar {
        \"\"\"
        Calculates the Discounted Cash Flow.
        \"\"\"
        let npv = npv(rate, cashflows)
        return npv
    }
    """
    ast = parse_valuascript(script)
    func = ast["function_definitions"][0]

    assert func["type"] == "function_definition"
    assert func["name"] == "calculate_dcf"
    assert func["return_type"] == "scalar"
    assert "Calculates the Discounted Cash Flow." in func["docstring"]

    # Parameters
    assert len(func["params"]) == 2
    assert func["params"][0] == {"name": "rate", "type": "scalar"}
    assert func["params"][1] == {"name": "cashflows", "type": "vector"}

    # Body
    assert len(func["body"]) == 2
    assert func["body"][0]["type"] == "execution_assignment"  # The 'let' statement
    assert func["body"][1]["type"] == "return_statement"


def test_function_with_tuple_return_parsing():
    """Tests function definitions with multiple return values."""
    script = """
    func get_revenue_and_ebit(data: vector) -> (vector, vector) {
        let revenue = data[0]
        let ebit = data[1]
        return (revenue, ebit)
    }
    """
    ast = parse_valuascript(script)
    func = ast["function_definitions"][0]

    assert func["name"] == "get_revenue_and_ebit"
    assert func["return_type"] == ["vector", "vector"]

    ret_stmt = func["body"][-1]
    assert ret_stmt["type"] == "return_statement"
    assert "values" in ret_stmt  # Key for multi-return
    assert len(ret_stmt["values"]) == 2


# --- 4. Module Parsing Test ---


def test_module_file_parsing():
    """
    A module can contain directives and function definitions,
    but no global 'let' assignments.
    """
    script = """
    @module
    @import "another_module.vs"

    func my_helper() -> scalar {
        return 1
    }
    """
    ast = parse_valuascript(script)

    assert len(ast["directives"]) == 1
    assert ast["directives"][0]["name"] == "module"
    assert len(ast["imports"]) == 1
    assert len(ast["function_definitions"]) == 1
    assert len(ast["execution_steps"]) == 0  # Crucial check


# --- 5. Syntax Error Tests ---


@pytest.mark.parametrize(
    "bad_code, expected_error_code",
    [("let x =", ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS), ("let y", ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT), ("@iterations =", ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS)],
)
def test_custom_syntax_errors(bad_code, expected_error_code):
    """
    Tests our pre-parsing checks that raise specific, user-friendly errors.
    """
    with pytest.raises(ValuaScriptError) as excinfo:
        parse_valuascript(bad_code)

    # Check that the raised exception has the correct custom error code
    assert excinfo.value.code == expected_error_code


def test_lark_unmatched_parenthesis_error():
    """
    Tests that a generic Lark parsing error (not caught by our pre-checks)
    is still raised, allowing the CLI to format it.
    """
    bad_code = "let x = (1 + 2"

    # We expect a generic UnexpectedInput from Lark because our pre-checks don't
    # look for this specific error.
    with pytest.raises(UnexpectedInput):
        parse_valuascript(bad_code)


# In tests/ast/test_ast_phase.py


def test_whitespace_and_comment_invariance():
    """
    Tests that the parser is not affected by non-semantic whitespace,
    blank lines, or comments.
    """
    script_with_messy_format = """
    # This is a leading comment.

    @iterations   =   1000   # Directive with comments.

    let x = 1 # Initial value

        # Indented comment
    let y = x + 2


    func my_func( a: scalar ) -> scalar {
        return a*2 # Return statement with comment
    }
    """
    script_with_clean_format = """
    @iterations = 1000
    let x = 1
    let y = x + 2
    func my_func(a: scalar) -> scalar {
        return a * 2
    }
    """

    messy_ast = parse_valuascript(script_with_messy_format)
    clean_ast = parse_valuascript(script_with_clean_format)

    # Ignore line numbers for this comparison
    def strip_line_numbers(d):
        if isinstance(d, dict):
            d.pop("line", None)
            for v in d.values():
                strip_line_numbers(v)
        elif isinstance(d, list):
            for i in d:
                strip_line_numbers(i)
        return d

    assert strip_line_numbers(messy_ast) == strip_line_numbers(clean_ast)


def test_numeric_literal_edge_cases():
    """Tests various formats of numeric literals."""
    script = """
    let neg_int = -10
    let neg_float = -0.5
    let leading_dot = 0.5
    let with_underscores = 1_000_000.500_000
    """
    ast = parse_valuascript(script)
    steps = ast["execution_steps"]
    assert steps[0]["value"] == -10
    assert steps[1]["value"] == -0.5
    assert steps[2]["value"] == 0.5
    assert steps[3]["value"] == 1000000.5


def test_vector_edge_cases():
    """Tests empty, single, and complex vectors."""
    script = "let my_vector = [1, some_var, Normal(0, 1)]"
    ast = parse_valuascript(script)
    vector_node = ast["execution_steps"][0]["items"]  # The vector itself is the value
    assert isinstance(vector_node, list)
    assert len(vector_node) == 3
    assert vector_node[0] == 1
    assert vector_node[1].value == "some_var"
    assert vector_node[2]["function"] == "Normal"


def test_empty_vector_and_string():
    """Ensures empty constructs are parsed correctly."""
    script = """
    let empty_vec = []
    let empty_str = ""
    """
    ast = parse_valuascript(script)
    steps = ast["execution_steps"]
    assert steps[0]["items"] == []
    assert steps[1]["value"].value == ""  # Access the value inside the _StringLiteral class


# In tests/ast/test_ast_phase.py


def test_conditional_as_function_argument():
    """Tests a conditional expression nested inside a function call."""
    script = "let result = Process(if is_risky then 0.9 else 0.5, 100)"
    ast = parse_valuascript(script)
    print(ast)
    func_call = ast["execution_steps"][0]

    assert func_call["function"] == "Process"
    assert len(func_call["args"]) == 2

    conditional_arg = func_call["args"][0]
    assert conditional_arg["type"] == "conditional_expression"
    assert conditional_arg["condition"] == "is_risky"
    assert conditional_arg["then_expr"] == 0.9
    assert conditional_arg["else_expr"] == 0.5

    assert func_call["args"][1] == 100


def test_function_with_no_parameters():
    """Tests that a function with an empty parameter list is parsed correctly."""
    script = "func get_default_rate() -> scalar { return 0.05 }"
    ast = parse_valuascript(script)
    func = ast["function_definitions"][0]
    assert func["name"] == "get_default_rate"
    assert len(func["params"]) == 0


def test_empty_and_whitespace_only_files():
    """An empty or whitespace-only script should produce an empty but valid AST."""
    for content in ["", "   \n\n   \t   \n"]:
        ast = parse_valuascript(content)
        assert len(ast["imports"]) == 0
        assert len(ast["directives"]) == 0
        assert len(ast["execution_steps"]) == 0
        assert len(ast["function_definitions"]) == 0


@pytest.mark.parametrize(
    "invalid_script",
    [
        # Mismatched delimiters
        "let x = [1, 2)",
        "func a() -> scalar ( return 1 }",
        "let y = (1, 2]",
        # Invalid assignment targets
        "let 1 = x",
        'let "hello" = y',
        "let (a, b) = my_func()",  # Tuples are not valid on the left side of 'let'
        # Incomplete statements
        "let x, = my_func()",
        "let ,y = my_func()",
        "let x, y, = my_func()",
        "func my_func(a:) -> scalar { return a }",  # Missing type
        "func my_func(a: scalar) -> { return a }",  # Missing return type
    ],
)
def test_guaranteed_lark_parsing_failures(invalid_script):
    """
    Tests a variety of fundamental syntax errors that should be caught by the
    Lark parser itself. The goal is to ensure they DO NOT parse successfully.
    """
    with pytest.raises(UnexpectedInput) as excinfo:
        parse_valuascript(invalid_script)

    # This assertion is optional but good practice. It confirms that an exception
    # was indeed raised and caught by pytest.raises.
    assert excinfo.type is lark.exceptions.UnexpectedCharacters


def test_empty_and_whitespace_only_files():
    """An empty or whitespace-only script should produce an empty but valid AST."""
    for content in ["", "   \n\n   \t   \n", "# Just a comment"]:
        ast = parse_valuascript(content)
        assert len(ast["imports"]) == 0
        assert len(ast["directives"]) == 0
        assert len(ast["execution_steps"]) == 0
        assert len(ast["function_definitions"]) == 0


def test_delete_element_syntax():
    """Tests the special syntax for deleting an element from a vector."""
    script = "let shorter_vector = my_vector[:2]"
    ast = parse_valuascript(script)
    step = ast["execution_steps"][0]

    assert step["type"] == "execution_assignment"
    assert step["result"] == "shorter_vector"
    assert step["function"] == "delete_element"
    assert len(step["args"]) == 2
    assert step["args"][0].value == "my_vector"
    assert step["args"][1] == 2


def test_expression_as_vector_index():
    """Tests that a complex expression is correctly parsed as a vector index."""
    script = "let item = my_vector[some_index + 1]"
    ast = parse_valuascript(script)
    step = ast["execution_steps"][0]

    assert step["type"] == "execution_assignment"
    assert step["result"] == "item"
    assert step["function"] == "get_element"

    # The second argument should be the AST for the 'some_index + 1' expression
    index_expression_node = step["args"][1]
    assert isinstance(index_expression_node, dict)
    assert index_expression_node["function"] == "add"
    assert index_expression_node["args"][0].value == "some_index"
    assert index_expression_node["args"][1] == 1
