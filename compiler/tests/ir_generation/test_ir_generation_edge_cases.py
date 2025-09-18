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
    script = dedent(
        """
    @iterations=1
    @output=z
    func get_value(v: scalar) -> scalar {
        return v * 10
    }
    let selector = true
    let z = if selector then get_value(5) else 0
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    assert ir[0]["type"] == "literal_assignment"  # let selector = true

    # The 'get_value(5)' call is lifted and inlined *before* the conditional assignment.
    # 1. Parameter assignment for the inlined call
    assert ir[1] == {"type": "execution_assignment", "result": ["__get_value_1__v"], "function": "identity", "args": [5], "line": 7}
    # 2. The return expression is calculated and stored in a temporary variable.
    assert ir[2] == {
        "type": "execution_assignment",
        "result": ["__temp_1"],
        "function": "multiply",
        "args": ["__get_value_1__v", 10],
        "line": 7,
    }
    # 3. The conditional assignment now uses the temporary variable.
    assert ir[3] == {
        "type": "conditional_assignment",
        "result": ["z"],
        "condition": "selector",
        "then_expr": "__temp_1",
        "else_expr": 0,
        "line": 7,
    }


def test_ir_for_conditional_logic_inside_udf(tmp_path):
    """
    Tests that an if/else block inside a UDF is correctly flattened and mangled.
    """
    script = dedent(
        """
    @iterations=1
    @output=result
    func get_bonus(sales: scalar) -> scalar {
        let is_high = sales > 1000
        let bonus = if is_high then 50 else 0
        return sales + bonus
    }
    let result = get_bonus(1200)
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    print(ir)

    # Inlining of get_bonus(1200)
    # 1. Parameter assignment
    assert ir[0]["result"] == ["__get_bonus_1__sales"]

    # 2. Body of the UDF with mangled variables
    assert ir[1] == {
        "type": "execution_assignment",
        "result": ["__get_bonus_1__is_high"],
        "function": "__gt__",
        "args": ["__get_bonus_1__sales", 1000],
        "line": 4,
    }
    assert ir[2] == {
        "type": "conditional_assignment",
        "result": ["__get_bonus_1__bonus"],
        "condition": "__get_bonus_1__is_high",
        "then_expr": 50,
        "else_expr": 0,
        "line": 5,
    }

    # 3. Final assignment from the return statement
    assert ir[3] == {
        "type": "execution_assignment",
        "result": ["result"],
        "function": "add",
        "args": ["__get_bonus_1__sales", "__get_bonus_1__bonus"],
        "line": 8,
    }


# --- 2. Complex Nested Expressions ---


def test_ir_for_nested_call_as_udf_argument(tmp_path):
    """
    Tests that a UDF call (inner) passed as an argument to another UDF (outer)
    is correctly resolved into a temporary variable first.
    """
    script = dedent(
        """
    @iterations=1
    @output=z
    func inner() -> scalar { return 5 }
    func outer(val: scalar) -> scalar { return val * 2 }
    let z = outer(inner())
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Inlining of inner() to a temp variable first
    assert ir[0] == {"type": "literal_assignment", "result": ["__temp_1"], "value": 5, "line": 5}

    # Inlining of outer(__temp_1)
    assert ir[1] == {"type": "execution_assignment", "result": ["__outer_1__val"], "function": "identity", "args": ["__temp_1"], "line": 5}
    assert ir[2] == {"type": "execution_assignment", "result": ["z"], "function": "multiply", "args": ["__outer_1__val", 2], "line": 5}


def test_ir_for_deeply_nested_expression_in_return(tmp_path):
    """
    Tests if a complex expression in a UDF's return statement is correctly
    lifted and inlined at the call site.
    """
    script = dedent(
        """
    @iterations=1
    @output=z
    func add_n(a: scalar, b: scalar) -> scalar { return a + b }
    func calculate(x: scalar) -> scalar {
        return add_n(x, 10) * 2
    }
    let z = calculate(5)
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Inlining calculate(5)
    assert ir[0]["result"] == ["__calculate_1__x"]  # Parameter assignment

    # The expression `add(__calculate_1__x, 10)` is a nested UDF call.
    # It gets inlined and its result is stored in a temporary variable.
    assert ir[1]["result"] == ["__add_n_1__a"]
    assert ir[2]["result"] == ["__add_n_1__b"]
    assert ir[3] == {
        "type": "execution_assignment",
        "result": ["__temp_1"],
        "function": "add",
        "args": ["__add_n_1__a", "__add_n_1__b"],
        "line": 5,
    }

    # The final assignment uses the temporary variable for the multiply operation.
    assert ir[4] == {"type": "execution_assignment", "result": ["z"], "function": "multiply", "args": ["__temp_1", 2], "line": 7}


# --- 3. Multi-Assignment Edge Cases ---


def test_ir_for_multi_assignment_from_nested_udf(tmp_path):
    """
    Tests that multi-assignment works correctly when the UDF it calls
    internally calls another UDF.
    """
    script = dedent(
        """
    @iterations=1
    @output=c
    func get_coords() -> (scalar, scalar) { return (10, 20) }
    func process_coords() -> (scalar, scalar) {
        let x, y = get_coords()
        return (x, y)
    }
    let a, c = process_coords()
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Inlining process_coords()
    # It first encounters the call to get_coords()
    # The return from `get_coords` is stored in mangled temp vars `__process_coords_1__x` and `__process_coords_1__y`
    assert ir[0]["type"] == "execution_assignment"
    assert ir[0]["result"] == ["__process_coords_1__x", "__process_coords_1__y"]
    assert ir[0]["function"] == "identity"
    # Note the nested structure of the args
    assert ir[0]["args"][0][0] == 10
    assert ir[0]["args"][0][1] == 20

    # The return statement of process_coords() is then processed
    assert ir[1]["type"] == "execution_assignment"
    assert ir[1]["result"] == ["a", "c"]
    assert ir[1]["function"] == "identity"
    assert ir[1]["args"] == [["__process_coords_1__x", "__process_coords_1__y"]]


def test_ir_for_udf_returning_literal_vector(tmp_path):
    """
    A simple case to ensure literal vectors returned by UDFs are handled cleanly.
    """
    script = dedent(
        """
    @iterations=1
    @output=v
    func get_constants() -> vector {
        return [10, 20, 30]
    }
    let v = get_constants()
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # The entire UDF call should be optimized down to a single literal assignment.
    assert len(ir) == 1
    assert ir[0] == {
        "type": "literal_assignment",
        "result": ["v"],
        "value": [10, 20, 30],
        "line": 6,
    }


# --- 4. Battle-Hardened Stress Tests ---


def test_ir_for_udf_in_conditional_condition(tmp_path):
    """Tests that a UDF returning a boolean is inlined correctly as a condition."""
    script = dedent(
        """
    @iterations=1
    @output=z
    func is_ready() -> boolean { return true }
    let z = if is_ready() then 1 else 0
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # 1. The call to `is_ready()` is inlined into a temporary variable.
    assert ir[0] == {"type": "literal_assignment", "result": ["__temp_1"], "value": True, "line": 4}
    # 2. The conditional assignment uses this temporary variable as its condition.
    assert ir[1] == {
        "type": "conditional_assignment",
        "result": ["z"],
        "condition": "__temp_1",
        "then_expr": 1,
        "else_expr": 0,
        "line": 4,
    }


def test_ir_for_vector_manipulation_through_udfs(tmp_path):
    """Tests that vectors flow through UDFs correctly."""
    script = dedent(
        """
    @iterations=1
    @output=z
    func get_data() -> vector { return [10, 20, 30] }
    func process_data(data: vector) -> scalar {
        let item = data[1] # get_element(data, 1)
        return item
    }
    let z = process_data(get_data())
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # 1. `get_data()` is inlined and its result is stored in a temporary variable.
    assert ir[0] == {"type": "literal_assignment", "result": ["__temp_1"], "value": [10, 20, 30], "line": 8}

    # 2. Inlining `process_data`: the temp var is assigned to the mangled parameter.
    assert ir[1] == {"type": "execution_assignment", "result": ["__process_data_1__data"], "function": "identity", "args": ["__temp_1"], "line": 8}

    # 3. The body of `process_data` is inlined, using the mangled parameter.
    assert ir[2] == {"type": "execution_assignment", "result": ["__process_data_1__item"], "function": "get_element", "args": ["__process_data_1__data", 1], "line": 5}

    # 4. The final assignment uses the mangled return variable.
    assert ir[3] == {"type": "execution_assignment", "result": ["z"], "function": "identity", "args": ["__process_data_1__item"], "line": 8}


def test_ir_for_deeply_nested_non_recursive_call_chain(tmp_path):
    """Stress-tests the mangling and temp var generation for deep call chains."""
    script = dedent(
        """
    @iterations=1
    @output=z
    func f3(a: scalar) -> scalar { return a + 1 }
    func f2(b: scalar) -> scalar { return f3(b) * 2 }
    func f1(c: scalar) -> scalar { return f2(c) - 3 }
    let z = f1(10)
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # Trace the inlining from the inside out:
    # 1. Inlining `f1(10)` starts. Its parameter `c` gets 10.
    assert ir[0]["result"] == ["__f1_1__c"] and ir[0]["args"] == [10]

    # 2. Inside `f1`, it calls `f2(__f1_1__c)`. This must be inlined to a temp var.
    #    This starts by inlining `f3` from within `f2`.
    assert ir[1]["result"] == ["__f2_1__b"]  # `f2`'s parameter `b` gets `__f1_1__c`
    assert ir[2]["result"] == ["__f3_1__a"]  # `f3`'s parameter `a` gets `__f2_1__b`
    assert ir[3]["result"] == ["__temp_2"] and ir[3]["function"] == "add"  # `f3` returns `a+1` to temp

    # 3. The rest of `f2`'s body (`* 2`) executes, storing in another temp var.
    assert ir[4]["result"] == ["__temp_1"] and ir[4]["function"] == "multiply"  # `f2` returns to temp

    # 4. Finally, the rest of `f1`'s body (`- 3`) executes for the final result.
    assert ir[5]["result"] == ["z"] and ir[5]["function"] == "subtract"


def test_ir_for_udf_returning_builtin_call(tmp_path):
    """Checks if a UDF returning a built-in call is optimized correctly."""
    script = dedent(
        """
    @iterations=1
    @output=z
    func get_sample() -> scalar {
        return Normal(0, 1)
    }
    let z = get_sample()
    """
    ).strip()
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    ir = run_ir_generation_pipeline(script, file_path)

    # The call to `get_sample()` should be directly replaced by the `Normal` call,
    # not an `identity` call to a mangled variable.
    assert len(ir) == 1
    assert ir[0] == {
        "type": "execution_assignment",
        "result": ["z"],
        "function": "Normal",
        "args": [0, 1],
        "line": 6,
    }
