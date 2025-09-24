import pytest
from pathlib import Path
from textwrap import dedent

# --- Test Dependencies ---
from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.ir_generator import generate_ir
from vsc.optimizer.ir_validator import IRValidator, IRValidationError
from vsc.optimizer.copy_propagation import run_copy_propagation
from vsc.optimizer.alias_resolver import run_alias_resolver
from vsc.optimizer.constant_folding import run_constant_folding
from vsc.optimizer.dead_code_elimination import run_dce
from vsc.optimizer.tuple_forwarding import run_tuple_forwarding

# --- Test Helpers ---


def create_dummy_file(directory, filename, content):
    script_content = dedent(content).strip()
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script_content)
    return str(path)


def run_full_pipeline_to_dce(script_content: str, file_path: str) -> list:
    """
    Runs the full pipeline up to and including Dead Code Elimination,
    validating every intermediate step.
    """
    ast = parse_valuascript(dedent(script_content).strip())
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)

    try:
        initial_ir = generate_ir(validated_model)
        IRValidator(initial_ir).validate()

        post_copy_prop = run_copy_propagation(initial_ir)
        IRValidator(post_copy_prop).validate()

        post_tuple_fwd = run_tuple_forwarding(post_copy_prop)
        IRValidator(post_tuple_fwd).validate()

        post_alias_elim = run_alias_resolver(post_tuple_fwd)
        IRValidator(post_alias_elim).validate()

        post_const_fold = run_constant_folding(post_alias_elim)
        IRValidator(post_const_fold).validate()

        final_ir = run_dce(post_const_fold, validated_model)
        IRValidator(final_ir).validate()
    except IRValidationError as e:
        pytest.fail(f"An intermediate stage produced an invalid IR: {e}")

    return final_ir


# --- Test Cases ---


def test_removes_simple_unused_variable(tmp_path):
    """The most basic case: a single unused variable should be eliminated."""
    script = """
    @iterations=1
    @output=y
    let x = 10  # Dead code
    let y = 20
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    final_ir = run_full_pipeline_to_dce(script, file_path)

    assert len(final_ir) == 1
    assert final_ir[0]["result"] == ["y"]
    assert final_ir[0]["value"] == 20


def test_removes_chain_of_unused_variables(tmp_path):
    """If a chain of dependencies is not used, the entire chain should be removed."""
    script = """
    @iterations=1
    @output=z
    let a = 10          # Dead
    let b = a + 5       # Dead
    let c = b * 2       # Dead
    let z = 100         # Live
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    final_ir = run_full_pipeline_to_dce(script, file_path)

    assert len(final_ir) == 1
    assert final_ir[0]["result"] == ["z"]


def test_keeps_dependencies_of_output_variable(tmp_path):
    """
    Ensures that variables required for the output are preserved,
    but also accepts that constant folding will optimize them away if possible.
    """
    script = """
    @iterations=1
    @output=c
    let a = 10
    let b = a + 5
    let c = b * 2
    let z = 100
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    final_ir = run_full_pipeline_to_dce(script, file_path)

    print(final_ir)

    assert len(final_ir) == 1
    final_step = final_ir[0]
    assert final_step["result"] == ["c"]
    assert final_step["value"] == 30


def test_dce_after_constant_folding(tmp_path):
    """
    Tests the synergy between constant folding and DCE. Folding an 'if'
    creates dead code that DCE should then remove.
    """
    script = """
    @iterations=1
    @output=z
    let selector = false
    let dead_var = 100
    let z = if selector then dead_var else 50
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    final_ir = run_full_pipeline_to_dce(script, file_path)

    # Constant folding evaluates `if false...` to just `50`.
    # This makes `dead_var` unused AND `selector` unused.
    # Therefore, DCE should eliminate both, leaving only the final result.
    assert len(final_ir) == 1
    final_step = final_ir[0]
    assert final_step["result"] == ["z"]
    assert final_step["value"] == 50


def test_dce_with_multi_assignment(tmp_path):
    """
    If any variable in a multi-assignment is live, the entire instruction must be kept.
    """
    script = """
    @iterations=1
    @output=b
    func get_pair() -> (scalar, scalar) { return (1, 2) }
    let a, b = get_pair()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    final_ir = run_full_pipeline_to_dce(script, file_path)

    assert len(final_ir) == 1
    assert final_ir[0]["result"] == ["a", "b"]


def test_validator_catches_ir_corrupted_by_buggy_dce(tmp_path):
    """
    This is a meta-test to ensure our validator works as a safety net.
    It simulates a scenario where a buggy DCE pass incorrectly removes a
    live variable, and confirms that the IRValidator catches the error.
    """
    script = """
    @iterations=1
    @output=z
    let a = 10      # This is live, as 'b' depends on it.
    let b = a + 5
    let c = Normal(1, 0.1)
    let z = b + c
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)

    # 1. Run the full pipeline to get the CORRECTLY optimized IR.
    # We expect this to contain definitions for both 'a' and 'b'.
    correctly_optimized_ir = run_full_pipeline_to_dce(script, file_path)
    assert len(correctly_optimized_ir) == 2  # Sanity check

    # 2. Manually corrupt the IR to simulate a bug in DCE.
    # We will pretend DCE incorrectly removed the definition of 'a'.
    corrupted_ir = [step for step in correctly_optimized_ir if step.get("result") != ["c"]]

    # The corrupted IR now only contains the definition for 'b', which uses 'a'.
    print(correctly_optimized_ir)
    assert len(corrupted_ir) == 1
    assert corrupted_ir[0]["result"] == ["z"]

    # 3. Assert that the IRValidator catches this corruption.
    with pytest.raises(IRValidationError) as excinfo:
        # We call the validator directly on the corrupted IR.
        IRValidator(corrupted_ir).validate()

    # The validator must report that 'a' is undefined in the first step of the corrupted IR.
    assert excinfo.value.step_index == 0
    assert excinfo.value.undefined_variables == ["c"]
