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
from vsc.optimizer.ir_validator import IRValidator, IRValidationError

# --- Test Helpers ---


def create_dummy_file(directory, filename, content):
    script_content = dedent(content).strip()
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script_content)
    return str(path)


def run_ir_generation_pipeline(script_content: str, file_path: str) -> list:
    script_content = dedent(script_content).strip()
    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)
    return generate_ir(validated_model)


def run_validated_copy_propagation(initial_ir: list) -> list:
    """
    A helper that validates the IR before and after running copy propagation.
    """
    try:
        # Validate the input IR from the generator
        IRValidator(initial_ir).validate()

        # Run the optimization
        optimized_ir = run_copy_propagation(initial_ir)

        # Validate the output IR from the optimizer
        IRValidator(optimized_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"Copy propagation produced an invalid IR: {e}")

    return optimized_ir


# --- 1. Baseline and Simple Propagation Tests ---


def test_no_identities_does_nothing(tmp_path):
    script = """
    @iterations=1
    @output=y
    let x = 10
    let y = x + 5
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)
    assert optimized_ir == initial_ir


def test_propagates_literal_value(tmp_path):
    script = """
    @iterations=1
    @output=y
    func my_add(p1: scalar) -> scalar {
        return p1 + 5
    }
    let y = my_add(100)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["function"] == "identity"
    assert final_step["args"][0]["function"] == "add"
    assert final_step["args"][0]["args"][0] == 100


def test_propagates_variable_name(tmp_path):
    script = """
    @iterations=1
    @output=y
    func my_multiply(p1: scalar) -> scalar {
        return p1 * 2
    }
    let x = 50
    let y = my_multiply(x)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    y_calc = optimized_ir[1]
    assert y_calc["function"] == "identity"
    assert y_calc["args"][0]["function"] == "multiply"
    assert y_calc["args"][0]["args"][0] == "x"


def test_propagates_variable_holding_stochastic_object(tmp_path):
    script = """
    @iterations=1
    @output=y
    func my_func(p: scalar) -> scalar {
        return p + 10
    }
    let random_x = Normal(1, 0.1)
    let y = my_func(random_x)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    y_calc = optimized_ir[1]
    assert y_calc["function"] == "identity"
    assert y_calc["args"][0]["function"] == "add"
    assert y_calc["args"][0]["args"][0] == "random_x"


def test_propagates_to_multiple_subsequent_uses(tmp_path):
    script = """
    @iterations=1
    @output=final_z
    func analyze(p: scalar) -> scalar {
        let y = p + 1
        let z = p - 1
        return z
    }
    let initial_val = 100
    let final_z = analyze(initial_val)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 4
    assert optimized_ir[1]["args"][0] == "initial_val"
    assert optimized_ir[2]["args"][0] == "initial_val"


# --- 2. Complex Propagation and Data Type Tests ---


def test_propagates_nested_expression_object(tmp_path):
    script = """
    @iterations=1
    @output=y
    func passthrough(p: scalar) -> scalar {
        return p
    }
    let y = passthrough(Normal(0, 1))
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    expected_ir = [{"type": "execution_assignment", "result": ["y"], "function": "identity", "args": [{"function": "Normal", "args": [0, 1]}], "line": 6}]
    assert optimized_ir == expected_ir


def test_handles_multiple_independent_identities(tmp_path):
    script = """
    @iterations=1
    @output=z
    func calculate(a: scalar, b: scalar) -> scalar {
        return a + b
    }
    let var_x = 5
    let z = calculate(10, var_x)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    z_calc = optimized_ir[1]
    assert z_calc["function"] == "identity"
    assert z_calc["args"][0]["function"] == "add"
    assert z_calc["args"][0]["args"] == [10, "var_x"]


def test_chained_identity_propagation(tmp_path):
    script = """
    @iterations=1
    @output=y
    func f1(p1: scalar) -> scalar { return p1 }
    func f2(p2: scalar) -> scalar { return f1(p2) }
    func f3(p3: scalar) -> scalar { return f2(p3) }
    let y = f3(100)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    expected_ir = [{"type": "execution_assignment", "result": ["y"], "function": "identity", "args": [100], "line": 6}]
    assert optimized_ir == expected_ir


def test_propagates_vector_literal(tmp_path):
    script = """
    @iterations=1
    @output=y
    func process_vector(p: vector) -> scalar {
        return p[0]
    }
    let y = process_vector([10, 20, 30])
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["function"] == "identity"
    assert final_step["args"][0]["function"] == "get_element"
    assert final_step["args"][0]["args"][0] == [10, 20, 30]


def test_multiple_calls_to_same_function_are_isolated(tmp_path):
    script = """
    @iterations=1
    @output=y
    func my_func(p: scalar) -> scalar {
        return p * 2
    }
    let x = my_func(10)
    let y = my_func(50)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    step1 = optimized_ir[0]
    assert step1["args"][0]["args"][0] == 10
    step2 = optimized_ir[1]
    assert step2["args"][0]["args"][0] == 50


def test_eliminates_identity_for_unused_parameter(tmp_path):
    script = """
    @iterations=1
    @output=y
    func ignore_param(p: scalar) -> scalar {
        return 1000
    }
    let y = ignore_param(Normal(0, 1))
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["type"] == "execution_assignment"
    assert final_step["function"] == "identity"
    assert final_step["args"] == [1000]


def test_does_not_affect_multi_return_identity(tmp_path):
    script = """
    @iterations=1
    @output=b
    func get_pair() -> (scalar, scalar) {
        return (10, 20)
    }
    let a, b = get_pair()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)
    assert optimized_ir == initial_ir


def test_propagates_into_deeply_nested_argument_structure(tmp_path):
    script = """
    @iterations=1
    @output=y
    func process_complex(data: vector) -> scalar {
        return data[2]
    }
    func outer(p: scalar) -> scalar {
        let temp_var = process_complex([10, 99, p, 101])
        return temp_var
    }
    let x = 50
    let y = outer(x)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    temp_var_assignment = optimized_ir[1]
    assert temp_var_assignment["function"] == "identity"
    get_element_call = temp_var_assignment["args"][0]
    assert get_element_call["function"] == "get_element"
    expected_arg_vector = [10, 99, "x", 101]
    assert get_element_call["args"][0] == expected_arg_vector


def test_propagated_variable_can_still_be_used_elsewhere(tmp_path):
    script = """
    @iterations=1
    @output=z
    func my_func(p: scalar) -> scalar {
        return p * 2
    }
    let x = 10
    let y = my_func(x)
    let z = x + y
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 3
    y_calculation = optimized_ir[1]
    assert y_calculation["function"] == "identity"
    assert y_calculation["args"][0]["function"] == "multiply"
    assert y_calculation["args"][0]["args"][0] == "x"

    z_calculation = optimized_ir[2]
    assert z_calculation["args"][0] == "x"


def test_works_correctly_with_imported_function_with_parameters(tmp_path):
    module_content = """
    @module
    func helper_add(val: scalar) -> scalar {
        return val + 100
    }
    """
    create_dummy_file(tmp_path, "module.vs", module_content)
    main_script = """
    @import "module.vs"
    @iterations=1
    @output=y
    let x = 50
    let y = helper_add(x)
    """
    main_path = create_dummy_file(tmp_path, "main.vs", main_script)
    initial_ir = run_ir_generation_pipeline(main_script, main_path)
    optimized_ir = run_validated_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    final_return_step = optimized_ir[1]
    assert final_return_step["function"] == "identity"
    assert final_return_step["args"][0]["function"] == "add"
    assert final_return_step["args"][0]["args"][0] == "x"
