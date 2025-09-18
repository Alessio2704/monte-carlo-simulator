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


# --- Test Helpers ---


def create_dummy_file(directory, filename, content):
    """Helper to create .vs files for the compiler pipeline."""
    # Use dedent to allow clean indentation in test scripts
    script_content = dedent(content).strip()
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script_content)
    return str(path)


def run_ir_generation_pipeline(script_content: str, file_path: str) -> list:
    """
    A helper that runs the full compiler front-end and returns the generated IR (pre-optimization).
    """
    script_content = dedent(script_content).strip()
    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)
    ir = generate_ir(validated_model)
    return ir


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
    optimized_ir = run_copy_propagation(initial_ir)
    assert optimized_ir == initial_ir
    assert len(optimized_ir) == 2


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
    assert initial_ir[0]["function"] == "identity"

    optimized_ir = run_copy_propagation(initial_ir)

    assert len(optimized_ir) == 1
    assert optimized_ir[0]["function"] == "add"
    assert optimized_ir[0]["args"][0] == 100


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
    optimized_ir = run_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    assert optimized_ir[1]["function"] == "multiply"
    assert optimized_ir[1]["args"][0] == "x"


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
    optimized_ir = run_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    assert optimized_ir[1]["function"] == "add"
    assert optimized_ir[1]["args"][0] == "random_x"


def test_propagates_to_multiple_subsequent_uses(tmp_path):
    """
    Ensures that a single identity variable is correctly replaced in all
    places it's used within the inlined function body.
    """
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

    optimized_ir = run_copy_propagation(initial_ir)

    # --- FIX: The test was wrong. This optimization phase does not
    # eliminate the final `return` assignment. It only propagates the
    # parameter. So we expect 4 steps, not 3.
    assert len(optimized_ir) == 4

    # We now check that the propagation was successful in the right places.
    # 0: let initial_val = 100
    assert optimized_ir[0]["result"] == ["initial_val"]
    # 1: let __analyze_1__y = initial_val + 1 (p was replaced)
    assert optimized_ir[1]["args"][0] == "initial_val"
    # 2: let __analyze_1__z = initial_val - 1 (p was replaced)
    assert optimized_ir[2]["args"][0] == "initial_val"
    # 3: let final_z = identity(__analyze_1__z)
    assert optimized_ir[3]["result"] == ["final_z"]


# --- 2. Complex Propagation and Data Type Tests ---


def test_propagates_nested_expression_object(tmp_path):
    """
    Tests that a complex object (like a nested function call dictionary)
    is correctly propagated.
    """
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

    optimized_ir = run_copy_propagation(initial_ir)

    # --- FIX: The test's hardcoded line number was wrong due to how
    # the script string was defined. The compiler correctly identified
    # the call site at line 6 of the stripped script.
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
    optimized_ir = run_copy_propagation(initial_ir)

    assert len(optimized_ir) == 2
    final_step = optimized_ir[1]
    assert final_step["function"] == "add"
    assert final_step["args"][0] == 10
    assert final_step["args"][1] == "var_x"


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
    optimized_ir = run_copy_propagation(initial_ir)

    expected_ir = [{"type": "execution_assignment", "result": ["y"], "function": "identity", "args": [100], "line": 6}]

    assert optimized_ir == expected_ir


# --- 3. Battle-Hardening and Interaction Tests ---


def test_propagates_vector_literal(tmp_path):
    """
    Tests that a vector literal is correctly propagated.
    """
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
    optimized_ir = run_copy_propagation(initial_ir)

    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["function"] == "get_element"
    # The first argument to get_element should be the propagated vector, not a mangled variable
    assert final_step["args"][0] == [10, 20, 30]


def test_multiple_calls_to_same_function_are_isolated(tmp_path):
    """
    CRITICAL TEST: Ensures that two separate calls to the same UDF do not
    have their optimizations interfere with each other. It must distinguish
    between `__my_func_1__p` and `__my_func_2__p`.
    """
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
    optimized_ir = run_copy_propagation(initial_ir)

    # We expect two final `execution_assignment` steps.
    assert len(optimized_ir) == 2

    # Check the first call's optimization
    step1 = optimized_ir[0]
    assert step1["result"] == ["x"]
    assert step1["function"] == "multiply"
    assert step1["args"][0] == 10  # Correctly propagated from the first call

    # Check the second call's optimization
    step2 = optimized_ir[1]
    assert step2["result"] == ["y"]
    assert step2["function"] == "multiply"
    assert step2["args"][0] == 50  # Correctly propagated from the second call


def test_eliminates_identity_for_unused_parameter(tmp_path):
    """
    Tests that the identity assignment for a parameter is removed even if
    that parameter is never used within the function body.
    """
    script = """
    @iterations=1
    @output=y
    func ignore_param(p: scalar) -> scalar {
        return 1000 # p is never used
    }
    let y = ignore_param(Normal(0, 1))
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    initial_ir = run_ir_generation_pipeline(script, file_path)

    # The initial IR will create an identity for 'p'
    assert len(initial_ir) == 2
    assert initial_ir[0]["function"] == "identity"

    optimized_ir = run_copy_propagation(initial_ir)

    # The optimizer should remove the useless identity assignment for 'p'
    # and leave only the final literal assignment.
    assert len(optimized_ir) == 1
    final_step = optimized_ir[0]
    assert final_step["type"] == "literal_assignment"
    assert final_step["result"] == ["y"]
    assert final_step["value"] == 1000


def test_works_correctly_with_imported_function_with_parameters(tmp_path):
    """
    This is the definitive test to prove the optimizer works on functions
    defined in imported modules that accept parameters.
    """
    # 1. Create the imported module file
    module_content = """
    @module
    func helper_add(val: scalar) -> scalar {
        # This function will cause a temporary identity to be created for 'val'
        return val + 100
    }
    """
    create_dummy_file(tmp_path, "module.vs", module_content)

    # 2. Create the main script that imports and calls the function
    main_script = """
    @import "module.vs"
    @iterations=1
    @output=y
    
    let x = 50
    let y = helper_add(x)
    """
    main_path = create_dummy_file(tmp_path, "main.vs", main_script)

    # 3. Run the pipeline
    initial_ir = run_ir_generation_pipeline(main_script, main_path)

    # 4. Assert the initial state is as expected
    # The IR should have a temp identity copy for the parameter 'val'
    assert len(initial_ir) == 3
    # Step 0: let x = 50
    # Step 1: let __helper_add_1__val = identity(x)  <- The one we want to eliminate
    assert initial_ir[1]["type"] == "execution_assignment"
    assert initial_ir[1]["function"] == "identity"
    assert initial_ir[1]["result"][0].startswith("__helper_add")
    assert initial_ir[1]["args"] == ["x"]
    # Step 2: let y = identity(...)

    # 5. Run the optimizer
    optimized_ir = run_copy_propagation(initial_ir)

    # 6. Assert the final optimized state
    # The temporary identity for the parameter should be gone.
    assert len(optimized_ir) == 2

    # The 'add' operation inside the function should now directly use 'x'
    final_add_step = optimized_ir[0]
    assert final_add_step["result"] == ["x"]  # This is the 'let x = 50' step

    final_return_step = optimized_ir[1]
    assert final_return_step["result"] == ["y"]
    assert final_return_step["function"] == "add"
    assert final_return_step["args"][0] == "x"  # Proof of propagation
    assert final_return_step["args"][1] == 100
