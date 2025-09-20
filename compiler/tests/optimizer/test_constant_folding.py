import pytest
from pathlib import Path
from textwrap import dedent

from vsc.optimizer.ir_validator import IRValidator, IRValidationError

# --- Test Dependencies ---
from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.ir_generator import generate_ir
from vsc.optimizer.copy_propagation import run_copy_propagation
from vsc.optimizer.identity_elimination import run_identity_elimination
from vsc.optimizer.constant_folding import run_constant_folding

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
    # 1. Frontend
    ast = parse_valuascript(dedent(script_content).strip())
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)

    # 2. IR Generation and Optimization Phases (with validation)
    initial_ir = generate_ir(validated_model)

    try:
        IRValidator(initial_ir).validate()

        post_copy_prop_ir = run_copy_propagation(initial_ir)
        IRValidator(post_copy_prop_ir).validate()

        post_identity_elim_ir = run_identity_elimination(post_copy_prop_ir)
        IRValidator(post_identity_elim_ir).validate()

        final_ir = run_constant_folding(post_identity_elim_ir)
        IRValidator(final_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"An optimization phase produced an invalid IR: {e}")

    return final_ir


# --- 1. Basic Folding Tests ---


def test_folds_simple_literal_expression(tmp_path):
    """Tests that 'let x = 1 + 2' becomes 'let x = 3'."""
    script = """
    @iterations=1
    @output=x
    let x = 1 + 2 * 3
    """  # Expected: 1 + 6 = 7
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    assert optimized_ir[0] == {"type": "literal_assignment", "result": ["x"], "value": 7, "line": 3}


def test_propagation_and_folding(tmp_path):
    """Tests that a constant is first propagated, then folded."""
    script = """
    @iterations=1
    @output=y
    let x = 10
    let y = x * (3 + 2)
    """  # Expected: 10 * 5 = 50
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    assert optimized_ir[0]["type"] == "literal_assignment"  # let x = 10
    assert optimized_ir[1] == {"type": "literal_assignment", "result": ["y"], "value": 50, "line": 4}


# --- 2. Incomplete and No-Op Tests ---


def test_does_not_fold_stochastic_functions(tmp_path):
    """Ensures that calls to Normal, Uniform, etc., are never folded."""
    script = """
    @iterations=1
    @output=x
    let x = Normal(0, 1)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # Get the IR after identity elimination
    initial_ir = run_full_pipeline_to_optimized_ir(script, file_path)
    # Rerun just the constant folding pass to isolate its behavior
    final_ir = run_constant_folding(initial_ir)

    # The IR should be unchanged because Normal() is not constant
    assert initial_ir == final_ir
    assert final_ir[0]["function"] == "Normal"


def test_partially_folds_expressions(tmp_path):
    """Tests that an expression with both constant and variable parts is simplified."""
    script = """
    @iterations=1
    @output=y
    let x = Normal(0, 1)
    let y = x + (10 * 5)
    """  # Expected: x + 50
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    y_assignment = optimized_ir[1]
    assert y_assignment["type"] == "execution_assignment"
    assert y_assignment["function"] == "add"
    assert y_assignment["args"] == ["x", 50]


# --- 3. Conditional Folding ---


def test_folds_conditional_with_constant_true_condition(tmp_path):
    """If the condition is a literal 'true', the else branch is eliminated."""
    script = """
    @iterations=1
    @output=x
    let should_run = true
    let x = if should_run then 100 else 200
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 2
    assert optimized_ir[1] == {"type": "literal_assignment", "result": ["x"], "value": 100, "line": 4}


def test_folds_conditional_with_constant_false_condition(tmp_path):
    """If the condition is a literal 'false', the then branch is eliminated."""
    script = """
    @iterations=1
    @output=x
    let x = if 1 > 2 then 100 else 200
    """  # 1 > 2 will be folded to false
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    assert len(optimized_ir) == 1
    assert optimized_ir[0] == {"type": "literal_assignment", "result": ["x"], "value": 200, "line": 3}


# --- 4. Integration Test ---


def test_full_pipeline_optimization_works_together(tmp_path):
    """
    A complex test to ensure copy prop, identity elim, and constant folding
    all work together correctly.
    """
    script = """
    @iterations=1
    @output=z
    func get_multiplier() -> scalar {
        return 2 * 5  # Should be folded to 10
    }
    func process(val: scalar) -> scalar {
        return val + get_multiplier()
    }
    let z = process(3)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    optimized_ir = run_full_pipeline_to_optimized_ir(script, file_path)

    # Expected flow:
    # 1. IR Gen inlines everything with lots of identities.
    # 2. Copy Prop simplifies parameter passing.
    # 3. Identity Elim simplifies return statements.
    # 4. Constant Folding evaluates `2*5` to `10`, then `3+10` to `13`.

    assert len(optimized_ir) == 1
    assert optimized_ir[0] == {"type": "literal_assignment", "result": ["z"], "value": 13, "line": 9}


def test_folder_safely_skips_non_assignment_nodes(tmp_path):
    """
    This is a regression test for a bug where the ConstantFolder crashed
    on 'return_statement' nodes found within an inlined UDF's IR.
    The folder must be able to handle instructions that are not assignments.
    """
    script = """
    @iterations=1
    @output=z
    # This UDF has an intermediate 'let', which is key to generating
    # a 'return_statement' IR node during inlining.
    func my_func(p: scalar) -> scalar {
        let intermediate = p * 2 
        return intermediate + 5
    }
    let z = my_func(10)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    try:
        # We use the full pipeline because the bug is an interaction
        # between the IR Generator and the Constant Folder.
        final_ir = run_full_pipeline_to_optimized_ir(script, file_path)

        print(final_ir)

        # The primary test is that the line above does not crash.
        # We can also assert the final folded value for completeness.
        # Expected: (10 * 2) + 5 = 25. DCE should leave only the final result.
        assert len(final_ir) == 1
        assert final_ir[0]["result"] == ["z"]
        assert final_ir[0]["value"] == 25

    except Exception as e:
        pytest.fail(f"ConstantFolder crashed on a valid script with an inlined return statement: {e}")
