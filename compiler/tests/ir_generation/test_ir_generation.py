import pytest
from pathlib import Path

from vsc.compiler import compile_valuascript
from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.ir_generator import generate_ir
from textwrap import dedent

# --- Test Helpers ---


def create_dummy_file(directory, filename, content):
    """Helper to create files for import tests."""
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)


def run_ir_generation_pipeline(script_content: str, file_path: str):
    """
    A helper that runs the full compiler front-end and returns the generated IR.
    """
    # Use dedent to handle multiline strings cleanly in tests
    from textwrap import dedent

    script_content = dedent(script_content)

    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)
    ir = generate_ir(validated_model)
    return ir


# --- 1. Basic Non-UDF Assignments ---


def test_ir_for_basic_literal_assignments(tmp_path):
    script = dedent(
        """
    @iterations=1
    @output=x
    let s = 10.5
    let b = true
    let v = [1, 2, 3]
    let str = "hello"
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0] == {"type": "literal_assignment", "result": ["s"], "value": 10.5, "line": 3}
    assert ir[1] == {"type": "literal_assignment", "result": ["b"], "value": True, "line": 4}
    assert ir[2] == {"type": "literal_assignment", "result": ["v"], "value": [1, 2, 3], "line": 5}
    assert ir[3] == {"type": "literal_assignment", "result": ["str"], "value": "hello", "line": 6}


def test_ir_for_execution_and_conditional_assignments(tmp_path):
    script = dedent(
        """
    @iterations=1
    @output=z
    let x = 1 + 2
    let y = Normal(0, 1)
    let z = if x > 2 then y else 0
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0] == {"type": "execution_assignment", "result": ["x"], "function": "add", "args": [1, 2], "line": 3}
    assert ir[1] == {"type": "execution_assignment", "result": ["y"], "function": "Normal", "args": [0, 1], "line": 4}
    assert ir[2] == {
        "type": "conditional_assignment",
        "result": ["z"],
        "condition": {"function": "__gt__", "args": ["x", 2]},
        "then_expr": "y",
        "else_expr": 0,
        "line": 5,
    }


# --- 2. Core UDF Inlining Tests ---


def test_ir_for_simple_udf_inlining_and_mangling(tmp_path):
    script = dedent(
        """
    @iterations=1
    @output=final_result
    func add_margin(revenue: scalar) -> scalar {
        let margin = 0.1
        let with_margin = revenue * (1 + margin)
        return with_margin
    }
    let initial_revenue = 1000
    let final_result = add_margin(initial_revenue)
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0]["type"] == "literal_assignment"
    assert ir[0]["result"] == ["initial_revenue"]

    # Inlining of 'add_margin' starts here
    # 1. Parameter assignment
    assert ir[1] == {
        "type": "execution_assignment",
        "result": ["__add_margin_1__revenue"],
        "function": "identity",
        "args": ["initial_revenue"],
        "line": 9,
    }
    # 2. Body statements with mangled variables
    assert ir[2] == {"type": "literal_assignment", "result": ["__add_margin_1__margin"], "value": 0.1, "line": 4}
    assert ir[3] == {
        "type": "execution_assignment",
        "result": ["__add_margin_1__with_margin"],
        "function": "multiply",
        "args": ["__add_margin_1__revenue", {"function": "add", "args": [1, "__add_margin_1__margin"]}],
        "line": 5,
    }
    # 3. Final assignment from return statement
    assert ir[4] == {
        "type": "execution_assignment",
        "result": ["final_result"],
        "function": "identity",
        "args": ["__add_margin_1__with_margin"],
        "line": 9,
    }


def test_ir_for_multiple_calls_to_same_udf(tmp_path):
    """Ensures mangling is unique for each call site."""
    script = dedent(
        """
    @iterations=1
    @output=y
    func my_identity(val: scalar) -> scalar {
        let internal = val
        return internal
    }
    let x = my_identity(10)
    let y = my_identity(20)
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # First call
    assert ir[0]["result"] == ["__my_identity_1__val"]
    assert ir[1]["result"] == ["__my_identity_1__internal"]
    assert ir[2]["result"] == ["x"]
    assert ir[2]["args"] == ["__my_identity_1__internal"]

    # Second call
    assert ir[3]["result"] == ["__my_identity_2__val"]
    assert ir[4]["result"] == ["__my_identity_2__internal"]
    assert ir[5]["result"] == ["y"]
    assert ir[5]["args"] == ["__my_identity_2__internal"]


# --- 3. UDF Inlining Edge Cases ---


def test_ir_for_udf_with_direct_return_expression(tmp_path):
    """Tests the optimization of lifting the return expression directly."""
    script = dedent(
        """
    @iterations=1
    @output=z
    func my_multiply(a: scalar, b: scalar) -> scalar {
        return a * b
    }
    let z = my_multiply(10, 20)
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Parameter assignments
    assert ir[0] == {"type": "execution_assignment", "result": ["__my_multiply_1__a"], "function": "identity", "args": [10], "line": 6}
    assert ir[1] == {"type": "execution_assignment", "result": ["__my_multiply_1__b"], "function": "identity", "args": [20], "line": 6}
    # The final assignment should be a 'multiply' operation, not an 'identity'
    assert ir[2] == {
        "type": "execution_assignment",
        "result": ["z"],
        "function": "multiply",
        "args": ["__my_multiply_1__a", "__my_multiply_1__b"],
        "line": 6,
    }


def test_ir_for_multi_assignment_from_udf(tmp_path):
    script = dedent(
        """
    @iterations=1
    @output=y
    func get_pair() -> (scalar, scalar) {
        let a = 1
        let b = 2
        return (a, b)
    }
    let x, y = get_pair()
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0] == {"type": "literal_assignment", "result": ["__get_pair_1__a"], "value": 1, "line": 4}
    assert ir[1] == {"type": "literal_assignment", "result": ["__get_pair_1__b"], "value": 2, "line": 5}
    # The return of a tuple becomes an identity assignment of a list
    assert ir[2] == {
        "type": "execution_assignment",
        "result": ["x", "y"],
        "function": "identity",
        "args": [["__get_pair_1__a", "__get_pair_1__b"]],
        "line": 8,
    }


def test_ir_for_udf_with_no_parameters(tmp_path):
    script = dedent(
        """
    @iterations=1
    @output=x
    func get_five() -> scalar { return 5 }
    let x = get_five()
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)
    # The entire call should be replaced by a single literal assignment
    assert len(ir) == 1
    assert ir[0] == {"type": "literal_assignment", "result": ["x"], "value": 5, "line": 4}


# --- 4. Imports and Nested Call Tests ---


def test_ir_for_inlining_udf_from_imported_module(tmp_path):
    module_content = dedent(
        """
    @module
    func helper(val: scalar) -> scalar {
        let result = val + 100
        return result
    }
    """
    ).strip()
    main_content = dedent(
        """
    @iterations=1
    @output=y
    @import "module.vs"
    let x = 50
    let y = helper(x)
    """
    ).strip()
    create_dummy_file(tmp_path, "module.vs", module_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)
    ir = run_ir_generation_pipeline(main_content, main_path)

    assert ir[0] == {"type": "literal_assignment", "result": ["x"], "value": 50, "line": 4}
    # Inlining of 'helper'
    assert ir[1]["result"] == ["__helper_1__val"]
    assert ir[2]["result"] == ["__helper_1__result"]
    assert ir[3]["result"] == ["y"]
    assert ir[3]["args"] == ["__helper_1__result"]
    assert ir[3]["line"] == 5  # Line of the call site in main.vs


def test_ir_for_nested_udf_calls(tmp_path):
    script = """
    @iterations=1
    @output=z
    func inner(a: scalar) -> scalar { return a * 2 }
    func outer(b: scalar) -> scalar { return inner(b) + 1 }
    let z = outer(10)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Inlining of outer(10) begins
    assert ir[0] == {"type": "execution_assignment", "result": ["__outer_1__b"], "function": "identity", "args": [10], "line": 6}

    # Inlining of the nested call to inner(__outer_1__b) begins.
    # It gets lifted to a temp variable.
    assert ir[1] == {"type": "execution_assignment", "result": ["__inner_1__a"], "function": "identity", "args": ["__outer_1__b"], "line": 5}
    assert ir[2] == {"type": "execution_assignment", "result": ["__temp_1"], "function": "multiply", "args": ["__inner_1__a", 2], "line": 5}

    # The original call `outer(10)` is finally resolved using the temp variable
    assert ir[3] == {"type": "execution_assignment", "result": ["z"], "function": "add", "args": ["__temp_1", 1], "line": 6}


# --- 5. Complex Expression Handling ---


def test_ir_for_nested_expressions_in_arguments(tmp_path):
    script = """
    @iterations=1
    @output=z
    let x = 10
    let y = true
    let z = sum_series([1, 2, if y then x else 0])
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert len(ir) == 3
    z_assignment = ir[2]
    assert z_assignment["function"] == "sum_series"

    # The argument should be a list containing the nested conditional expression object
    arg_list = z_assignment["args"][0]
    assert isinstance(arg_list, list)
    assert arg_list[0] == 1
    assert arg_list[1] == 2
    assert arg_list[2] == {
        "type": "conditional_expression",
        "condition": "y",
        "then_expr": "x",
        "else_expr": 0,
    }
