import pytest
from pathlib import Path
from textwrap import dedent

# Import the same test helpers from the existing test file
from .test_ir_generation import create_dummy_file, run_ir_generation_pipeline

# --- 1. Conditionals and UDF Interaction ---


def test_ir_for_udf_call_within_conditional_expression(tmp_path):
    """
    Tests that a UDF called inside an 'if' expression is correctly inlined.
    """
    script = """
    @iterations=1
    @output=z
    func get_value(v: scalar) -> scalar {
        return v * 10
    }
    let selector = true
    let z = if selector then get_value(5) else 0
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0]["type"] == "literal_assignment"  # let selector = true
    assert ir[1]["function"] == "identity"

    # The return expression is calculated and stored in a temp via an identity call.
    assert ir[2] == {
        "type": "execution_assignment",
        "result": ["__temp_1"],
        "function": "identity",
        "args": [{"function": "multiply", "args": ["__get_value_1__v", 10]}],
        "line": 7,
    }
    # The conditional assignment now uses the temporary variable.
    assert ir[3]["then_expr"] == "__temp_1"


def test_ir_for_conditional_logic_inside_udf(tmp_path):
    """
    Tests that an if/else block inside a UDF is correctly flattened and mangled.
    """
    script = """
    @iterations=1
    @output=result
    func get_bonus(sales: scalar) -> scalar {
        let is_high = sales > 1000
        let bonus = if is_high then 50 else 0
        return sales + bonus
    }
    let result = get_bonus(1200)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0]["result"] == ["__get_bonus_1__sales"]
    assert ir[1]["function"] == "__gt__"
    assert ir[2]["type"] == "conditional_assignment"

    # Final assignment from the return statement is now an identity call.
    assert ir[3] == {
        "type": "execution_assignment",
        "result": ["result"],
        "function": "identity",
        "args": [{"function": "add", "args": ["__get_bonus_1__sales", "__get_bonus_1__bonus"]}],
        "line": 8,
    }


# --- 2. Complex Nested Expressions ---


def test_ir_for_nested_call_as_udf_argument(tmp_path):
    """
    Tests that a UDF call (inner) passed as an argument to another UDF (outer)
    is correctly resolved into a temporary variable first.
    """
    script = """
    @iterations=1
    @output=z
    func inner() -> scalar { return 5 }
    func outer(val: scalar) -> scalar { return val * 2 }
    let z = outer(inner())
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Inlining of inner() to a temp variable first is now an identity call.
    assert ir[0] == {"type": "execution_assignment", "result": ["__temp_1"], "function": "identity", "args": [5], "line": 5}

    # Inlining of outer(__temp_1)
    assert ir[1]["function"] == "identity"
    assert ir[1]["args"] == ["__temp_1"]
    assert ir[2]["function"] == "identity"
    assert ir[2]["args"][0]["function"] == "multiply"


def test_ir_for_deeply_nested_expression_in_return(tmp_path):
    """
    Tests if a complex expression in a UDF's return statement is correctly
    lifted and inlined at the call site.
    """
    script = """
    @iterations=1
    @output=z
    func add_n(a: scalar, b: scalar) -> scalar { return a + b }
    func calculate(x: scalar) -> scalar {
        return add_n(x, 10) * 2
    }
    let z = calculate(5)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0]["result"] == ["__calculate_1__x"]
    assert ir[1]["result"] == ["__add_n_1__a"]
    assert ir[2]["result"] == ["__add_n_1__b"]

    # The return from `add_n` is an identity call into a temp var.
    assert ir[3]["function"] == "identity"
    assert ir[3]["args"][0]["function"] == "add"

    # The final assignment is an identity call of the whole expression.
    assert ir[4]["function"] == "identity"
    assert ir[4]["args"][0]["function"] == "multiply"


# --- 3. Multi-Assignment Edge Cases ---


def test_ir_for_multi_assignment_from_nested_udf(tmp_path):
    script = """
    @iterations=1
    @output=c
    func get_coords() -> (scalar, scalar) { return (10, 20) }
    func process_coords() -> (scalar, scalar) {
        let x, y = get_coords()
        return (x, y)
    }
    let a, c = process_coords()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Inlining process_coords() results in an identity of an identity
    assert ir[0]["function"] == "identity"
    assert ir[0]["args"][0] == [10, 20]  # inner return
    assert ir[1]["function"] == "identity"
    assert ir[1]["args"][0] == ["__process_coords_1__x", "__process_coords_1__y"]  # outer return


def test_ir_for_udf_returning_literal_vector(tmp_path):
    """
    Ensures literal vectors returned by UDFs are NOT optimized away by the generator.
    """
    script = """
    @iterations=1
    @output=v
    func get_constants() -> vector {
        return [10, 20, 30]
    }
    let v = get_constants()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert len(ir) == 1
    assert ir[0] == {
        "type": "execution_assignment",
        "result": ["v"],
        "function": "identity",
        "args": [[10, 20, 30]],
        "line": 6,
    }


# --- 4. Battle-Hardened Stress Tests ---


def test_ir_for_udf_in_conditional_condition(tmp_path):
    """Tests that a UDF returning a boolean is inlined correctly as a condition."""
    script = """
    @iterations=1
    @output=z
    func is_ready() -> boolean { return true }
    let z = if is_ready() then 1 else 0
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # The call to `is_ready()` is inlined into a temporary identity assignment.
    assert ir[0] == {"type": "execution_assignment", "result": ["__temp_1"], "function": "identity", "args": [True], "line": 4}
    assert ir[1]["condition"] == "__temp_1"


def test_ir_for_vector_manipulation_through_udfs(tmp_path):
    """Tests that vectors flow through UDFs correctly."""
    script = """
    @iterations=1
    @output=z
    func get_data() -> vector { return [10, 20, 30] }
    func process_data(data: vector) -> scalar {
        let item = data[1]
        return item
    }
    let z = process_data(get_data())
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # `get_data()` is inlined to a temp identity assignment.
    assert ir[0] == {"type": "execution_assignment", "result": ["__temp_1"], "function": "identity", "args": [[10, 20, 30]], "line": 8}
    assert ir[1]["function"] == "identity"
    assert ir[2]["function"] == "GetElement"
    assert ir[3]["function"] == "identity"


def test_ir_for_deeply_nested_non_recursive_call_chain(tmp_path):
    """Stress-tests the mangling and temp var generation for deep call chains."""
    script = """
    @iterations=1
    @output=z
    func f3(a: scalar) -> scalar { return a + 1 }
    func f2(b: scalar) -> scalar { return f3(b) * 2 }
    func f1(c: scalar) -> scalar { return f2(c) - 3 }
    let z = f1(10)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Asserting the chain of identities
    assert ir[3]["function"] == "identity"
    assert ir[3]["args"][0]["function"] == "add"
    assert ir[4]["function"] == "identity"
    assert ir[4]["args"][0]["function"] == "multiply"
    assert ir[5]["function"] == "identity"
    assert ir[5]["args"][0]["function"] == "subtract"


def test_ir_for_udf_returning_builtin_call(tmp_path):
    """Checks that a UDF returning a built-in call is not optimized."""
    script = """
    @iterations=1
    @output=z
    func get_sample() -> scalar {
        return Normal(0, 1)
    }
    let z = get_sample()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert len(ir) == 1
    assert ir[0] == {
        "type": "execution_assignment",
        "result": ["z"],
        "function": "identity",
        "args": [{"function": "Normal", "args": [0, 1]}],
        "line": 6,
    }


def test_ir_for_udf_with_string_literal_argument(tmp_path):
    """
    Tests that passing a string literal to a UDF does not cause a validation
    error, proving that the literal is not mistaken for a variable.
    This is a regression test for the 'call' bug.
    """
    script = """
    @iterations=1
    @output=op1

    func get_option1(type: string) -> scalar {
        let spot_price = 100
        let strike_price = 105
        let risk_free_rate = 0.05
        let time = 1
        let vol = 0.2
        let option_price = BlackScholes(spot_price, strike_price, risk_free_rate, time, vol, type)
        return option_price
    }

    let op1 = get_option1("call")
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # The test passes if run_ir_pipeline_with_validation does not raise an exception.
    ir = run_ir_generation_pipeline(script, file_path)

    # Optional: We can also assert something about the generated IR
    # to ensure the literal was handled correctly.
    param_passing_step = next((step for step in ir if step["result"] == ["__get_option1_1__type"]), None)
    assert param_passing_step is not None, "Could not find the parameter passing step in the IR"

    from vsc.parser.parser import _StringLiteral

    assert isinstance(param_passing_step["args"][0], _StringLiteral), "Argument should be a _StringLiteral"
    assert param_passing_step["args"][0].value == "call", "String literal value is incorrect"
