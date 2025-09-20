import pytest
from pathlib import Path
from textwrap import dedent

# --- Test Dependencies ---
from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.ir_generator import generate_ir
from vsc.optimizer.copy_propagation import run_copy_propagation
from vsc.optimizer.identity_elimination import run_identity_elimination

from vsc.optimizer.ir_validator import IRValidator, IRValidationError

# --- Test Helpers ---


def create_dummy_file(directory, filename, content):
    """Helper to create files for the test pipeline."""
    script_content = dedent(content).strip()
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script_content)
    return str(path)


def run_full_pipeline_to_optimized_ir(script_content: str, file_path: str) -> list:
    """
    Runs the entire compiler front-end and all optimization phases in order,
    VALIDATING THE IR AT EACH STEP.
    """
    script_content = dedent(script_content).strip()
    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)

    initial_ir = generate_ir(validated_model)

    try:
        IRValidator(initial_ir).validate()

        post_copy_prop_ir = run_copy_propagation(initial_ir)
        IRValidator(post_copy_prop_ir).validate()

        final_ir = run_identity_elimination(post_copy_prop_ir)
        IRValidator(final_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"An optimization phase produced an invalid IR: {e}")

    return final_ir


# --- 1. Core Simplification Tests ---


def test_eliminates_identity_wrapper_from_udf_return(tmp_path):
    """
    Tests the primary use case: a UDF with a direct return expression
    should have its 'identity' wrapper removed.
    """
    script = """
    @iterations=1
    @output=z
    func my_add(a: scalar, b: scalar) -> scalar {
        return a + b
    }
    let z = my_add(10, 20)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["type"] == "execution_assignment"
    assert final_step["result"] == ["z"]
    assert final_step["function"] == "add"
    assert final_step["args"] == [10, 20]


def test_eliminates_identity_on_deeply_nested_expression(tmp_path):
    """
    Ensures the optimization works even if the nested expression
    is itself complex.
    """
    script = """
    @iterations=1
    @output=z
    func complex_calc() -> scalar {
        return (1 + 2) * (10 - 5)
    }
    let z = complex_calc()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["function"] == "multiply"
    assert final_step["args"][0]["function"] == "add"
    assert final_step["args"][1]["function"] == "subtract"


def test_eliminates_identity_on_builtin_call(tmp_path):
    """
    Tests that a UDF returning a direct call to a built-in stochastic
    function is correctly simplified.
    """
    script = """
    @iterations=1
    @output=z
    func get_sample() -> scalar {
        return Normal(0, 1)
    }
    let z = get_sample()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    assert optimized_ir[0] == {
        "type": "execution_assignment",
        "result": ["z"],
        "function": "Normal",
        "args": [0, 1],
        "line": 6,
    }


# --- 2. Edge Case and No-Op Tests ---


def test_does_nothing_if_no_wrapper_exists(tmp_path):
    """
    An IR without the specific identity wrapper pattern should pass through unchanged.
    """
    script = """
    @iterations=1
    @output=y
    let x = 10 + 5
    let y = Normal(x, 1)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # We run the pipeline manually here to inspect intermediate steps
    initial_ir = generate_ir(validate_semantics(infer_types_and_taint(discover_symbols(parse_valuascript(script), file_path))))
    final_ir = run_identity_elimination(initial_ir)

    assert initial_ir == final_ir


def test_does_not_eliminate_identity_wrapping_a_literal(tmp_path):
    """
    An identity call wrapping a literal value (e.g., return 5)
    should NOT be modified by this pass.
    """
    script = """
    @iterations=1
    @output=x
    func get_five() -> scalar { return 5 }
    let x = get_five()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    # The IR still contains the identity call, as the argument is not a nested expression
    assert len(optimized_ir) == 1
    assert optimized_ir[0]["function"] == "identity"
    assert optimized_ir[0]["args"] == [5]


def test_does_not_eliminate_identity_wrapping_a_variable(tmp_path):
    """
    An identity call wrapping a variable (e.g., return my_var) should also
    remain untouched. Copy Propagation already handles these.
    """
    script = """
    @iterations=1
    @output=y
    func passthrough(x: scalar) -> scalar {
        return x
    }
    let initial = 100
    let y = passthrough(initial)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    # The final assignment to y is still an identity of 'initial'
    assert optimized_ir[1]["function"] == "identity"
    assert optimized_ir[1]["args"] == ["initial"]


def test_does_not_affect_multi_return_identity(tmp_path):
    """
    A multi-assignment from a UDF results in an identity call wrapping a
    list of variables. This must NOT be changed.
    """
    script = """
    @iterations=1
    @output=y
    func get_pair() -> (scalar, scalar) {
        return (10, 20)
    }
    let x, y = get_pair()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # Run pipeline up to just before our phase
    initial_ir = generate_ir(validate_semantics(infer_types_and_taint(discover_symbols(parse_valuascript(script), file_path))))
    post_copy_prop_ir = run_copy_propagation(initial_ir)

    # Run our phase
    final_ir = run_identity_elimination(post_copy_prop_ir)

    # The IR should be identical because the arg to identity() is a list, not a dict.
    assert post_copy_prop_ir == final_ir
    assert final_ir[0]["function"] == "identity"
    assert final_ir[0]["args"] == [[10, 20]]


# --- 3. Interaction with Other Phases ---


def test_works_correctly_after_copy_propagation(tmp_path):
    """
    This is a key integration test. Copy propagation first replaces a
    temporary variable, creating the pattern that this phase then cleans up.
    """
    script = """
    @iterations=1
    @output=y
    func multiply_n(p: scalar) -> scalar {
        return p * 10
    }
    let x = 50
    let y = multiply_n(x)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    y_assignment = optimized_ir[1]

    # The final assignment to 'y' is now a direct multiply_n call,
    # not an identity of a multiply_n call.
    assert y_assignment["function"] == "multiply"
    assert y_assignment["args"] == ["x", 10]


def test_works_on_chained_udf_calls(tmp_path):
    """
    Tests a chain of UDFs (f2 calls f1), ensuring the final result is
    fully simplified.
    """
    script = """
    @iterations=1
    @output=z
    func f1(a: scalar) -> scalar { return a + 1 }
    func f2(b: scalar) -> scalar { return f1(b) }
    let z = f2(100)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["result"] == ["z"]
    assert final_step["function"] == "add"
    assert final_step["args"] == [100, 1]
