import pytest
from vsc.optimizer.ir_validator import IRValidator, IRValidationError

# --- 1. Positive Tests (Should Pass) ---


def test_validator_on_valid_simple_ir():
    """Tests that a simple, correct IR passes validation."""
    valid_ir = [
        {"type": "literal_assignment", "result": ["x"], "value": 10},
        {"type": "execution_assignment", "result": ["y"], "function": "add", "args": ["x", 5]},
    ]
    try:
        IRValidator(valid_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"Validator failed unexpectedly on valid IR: {e}")


def test_validator_on_valid_complex_ir():
    """Tests that a more complex but correct IR passes validation."""
    valid_ir = [
        {"type": "literal_assignment", "result": ["a"], "value": 100},
        {"type": "literal_assignment", "result": ["b"], "value": 200},
        {"type": "literal_assignment", "result": ["cond"], "value": True},
        {"type": "conditional_assignment", "result": ["c"], "condition": "cond", "then_expr": "a", "else_expr": "b"},
        {"type": "execution_assignment", "result": ["d"], "function": "multiply", "args": ["c", 2]},
    ]
    try:
        IRValidator(valid_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"Validator failed unexpectedly on complex valid IR: {e}")


def test_validator_on_empty_ir():
    """An empty IR is, by definition, valid."""
    IRValidator([]).validate()


def test_validator_handles_mangled_names_correctly():
    """Ensures the validator works with post-inlining variable names."""
    valid_ir = [
        {"type": "literal_assignment", "result": ["__func_1__p"], "value": 50},
        {"type": "execution_assignment", "result": ["__func_1__result"], "function": "multiply", "args": ["__func_1__p", 2]},
        {"type": "execution_assignment", "result": ["final_var"], "function": "identity", "args": ["__func_1__result"]},
    ]
    try:
        IRValidator(valid_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"Validator failed on IR with mangled names: {e}")


# --- 2. Negative Tests (Should Fail) ---


def test_validator_fails_on_undefined_variable_in_expression():
    invalid_ir = [
        {"type": "execution_assignment", "result": ["y"], "function": "add", "args": ["x", 5]},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()

    assert excinfo.value.undefined_variables == ["x"]
    assert excinfo.value.step_index == 0


def test_validator_fails_on_out_of_order_definition():
    invalid_ir = [
        {"type": "execution_assignment", "result": ["y"], "function": "add", "args": ["x", 5]},
        {"type": "literal_assignment", "result": ["x"], "value": 10},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()

    assert excinfo.value.undefined_variables == ["x"]
    assert excinfo.value.step_index == 0


def test_validator_fails_on_undefined_variable_in_conditional_condition():
    invalid_ir = [
        {"type": "conditional_assignment", "result": ["c"], "condition": "is_true", "then_expr": 1, "else_expr": 0},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()
    assert excinfo.value.undefined_variables == ["is_true"]


# highlight-start
def test_validator_fails_on_undefined_variable_in_conditional_branch():
    """
    Checks for undefined variables in the 'then' or 'else' branches.
    This test is now order-independent.
    """
    invalid_ir = [
        {"type": "literal_assignment", "result": ["cond"], "value": True},
        {"type": "conditional_assignment", "result": ["c"], "condition": "cond", "then_expr": "a", "else_expr": "b"},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()

    # Use set comparison to make the test robust against ordering changes
    assert set(excinfo.value.undefined_variables) == {"a", "b"}
    assert excinfo.value.step_index == 1


# highlight-end


def test_validator_fails_on_use_before_define_in_first_step(tmp_path):
    invalid_ir = [
        {"type": "execution_assignment", "result": ["a", "b"], "args": [["c", "d"]]},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()

    assert excinfo.value.step_index == 0
    assert set(excinfo.value.undefined_variables) == {"c", "d"}


# highlight-start
def test_validator_fails_with_multiple_undefined_vars_in_one_step():
    """
    Explicitly tests that the validator collects ALL undefined variables
    from a single instruction before raising.
    """
    invalid_ir = [
        # Step 0: 'a', 'b', and 'c' are all undefined.
        {"type": "execution_assignment", "result": ["d"], "function": "add", "args": ["a", "b", "c"]},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()

    assert excinfo.value.step_index == 0
    # Check that all three are reported
    assert set(excinfo.value.undefined_variables) == {"a", "b", "c"}


# highlight-end

# --- 3. Multi-Assignment and Tuple Edge Cases ---


def test_validator_on_valid_multi_assignment():
    valid_ir = [
        {"type": "literal_assignment", "result": ["a", "b"], "value": [1, 2]},
        {"type": "execution_assignment", "result": ["c"], "function": "add", "args": ["a", "b"]},
    ]
    try:
        IRValidator(valid_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"Validator failed on valid multi-assignment IR: {e}")


def test_validator_fails_on_undefined_input_to_multi_assignment():
    invalid_ir = [
        {"type": "execution_assignment", "result": ["a", "b"], "function": "SomeFunc", "args": ["undefined_var"]},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()
    assert excinfo.value.undefined_variables == ["undefined_var"]


def test_validator_fails_on_self_referential_multi_assignment():
    invalid_ir = [
        {"type": "execution_assignment", "result": ["a", "b"], "function": "identity", "args": [[1, "a"]]},
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()

    assert excinfo.value.undefined_variables == ["a"]
    assert excinfo.value.step_index == 0


# --- 4. Complex and Nested Structure Tests ---


def test_validator_on_valid_nested_ir():
    valid_ir = [
        {"type": "literal_assignment", "result": ["my_var"], "value": 10},
        {"type": "literal_assignment", "result": ["my_cond"], "value": True},
        {
            "type": "execution_assignment",
            "result": ["z"],
            "function": "sum_series",
            "args": [[1, 2, {"type": "conditional_expression", "condition": "my_cond", "then_expr": "my_var", "else_expr": 0}]],
        },
    ]
    try:
        IRValidator(valid_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"Validator failed on valid nested IR: {e}")


def test_validator_fails_on_undefined_in_deeply_nested_ir():
    invalid_ir = [
        {"type": "literal_assignment", "result": ["my_cond"], "value": True},
        {
            "type": "execution_assignment",
            "result": ["z"],
            "function": "sum_series",
            "args": [[1, 2, {"type": "conditional_expression", "condition": "my_cond", "then_expr": "undefined_var", "else_expr": 0}]],
        },
    ]
    with pytest.raises(IRValidationError) as excinfo:
        IRValidator(invalid_ir).validate()

    assert excinfo.value.undefined_variables == ["undefined_var"]
    assert excinfo.value.step_index == 1
