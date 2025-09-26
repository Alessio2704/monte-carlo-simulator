import pytest
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Optional

# --- Test Dependencies ---
from vsc.parser.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.ir_generator import generate_ir
from vsc.optimizer.copy_propagation import run_copy_propagation
from vsc.optimizer.tuple_forwarding import run_tuple_forwarding
from vsc.optimizer.alias_resolver import run_alias_resolver
from vsc.optimizer.constant_folding import run_constant_folding
from vsc.optimizer.dead_code_elimination import run_dce
from vsc.ir_partitioner import partition_ir

# --- Test Helpers ---


def create_dummy_file(directory: Path, filename: str, content: str) -> str:
    path = directory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip())
    return str(path)


def run_full_pipeline_to_partitioned_ir(script_content: str, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    ast = parse_valuascript(dedent(script_content).strip())
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    validated_model = validate_semantics(enriched_table)
    initial_ir = generate_ir(validated_model)
    post_copy_prop = run_copy_propagation(initial_ir)
    post_tuple_fwd = run_tuple_forwarding(post_copy_prop)
    post_alias_elim = run_alias_resolver(post_tuple_fwd)
    post_const_fold = run_constant_folding(post_alias_elim)
    final_optimized_ir = run_dce(post_const_fold, validated_model)
    partitioned_result = partition_ir(final_optimized_ir, validated_model)
    return partitioned_result


def _get_step_for_variable(ir_list: List[Dict[str, Any]], var_name: str) -> Optional[Dict[str, Any]]:
    for step in ir_list:
        if var_name in step.get("result", []):
            return step
    return None


# --- 1. Purely Deterministic Conditional Edge Cases ---


def test_deterministic_nested_conditional_is_pre_trial(tmp_path):
    """Ensures a complex but fully deterministic nested conditional remains pre-trial."""
    script = """
    @iterations=1
    @output=z
    let v1_vec = GrowSerie(10,0,1)
    let v2_vec = GrowSerie(20,0,1)
    let v1 = v1_vec[0]
    let v2 = v2_vec[0]
    let z = if v1 > 5 then (if v2 < 30 then 100 else 200) else 300
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)

    assert len(partitioned["per_trial_steps"]) == 0
    z_step = _get_step_for_variable(partitioned["pre_trial_steps"], "z")
    assert z_step is not None
    assert z_step["type"] == "conditional_assignment"


def test_deterministic_udf_in_conditional_is_pre_trial(tmp_path):
    """A UDF call that is deterministic inside a conditional should remain pre-trial."""
    script = """
    @iterations=1
    @output=z
    func process(val: scalar) -> scalar { return val * 10 }
    let x_vec = GrowSerie(5,0,1)
    let x = x_vec[0]
    let z = if x > 0 then process(x) else 0
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)

    assert len(partitioned["per_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "x") is not None
    z_step = _get_step_for_variable(partitioned["pre_trial_steps"], "z")
    assert z_step is not None
    assert z_step["type"] == "conditional_assignment"


# --- 2. Nested Conditionals with Stochasticity ---


def test_taint_propagates_out_of_nested_conditional(tmp_path):
    script = """
    @iterations=1
    @output=z
    let s = Normal(0, 1)
    let d_vec = GrowSerie(10, 0, 1) # Use non-foldable function
    let d = d_vec[0]
    let cond1 = d > 5
    let cond2 = d < 15
    let z = if cond1 then (if cond2 then s else d) else d
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)

    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d_vec") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "cond1") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "cond2") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "s") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


def test_stochastic_outer_condition_taints_all(tmp_path):
    """If an outer condition is stochastic, the whole expression is per-trial, regardless of branches."""
    script = """
    @iterations=1
    @output=z
    let s_cond = Bernoulli(0.5) > 0
    let d1 = 10
    let d2 = 20
    let z = if s_cond then (if d1 > 5 then d1 else d2) else d2
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)

    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d1") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d2") is not None

    assert _get_step_for_variable(partitioned["per_trial_steps"], "s_cond") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


def test_stochastic_udf_in_conditional_branch(tmp_path):
    """A UDF with an internal stochastic source placed in a branch makes the result per-trial."""
    script = """
    @iterations=1
    @output=z
    func get_random() -> scalar { return Uniform(10, 20) }
    let z = if true then get_random() else 0
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)

    assert len(partitioned["pre_trial_steps"]) == 0
    z_step = _get_step_for_variable(partitioned["per_trial_steps"], "z")
    assert z_step is not None
    assert z_step["type"] == "execution_assignment"
    assert z_step["function"] == "Uniform"


def test_udf_with_stochastic_condition_is_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=z
    func flip_coin() -> boolean { return Bernoulli(0.5) > 0 }
    let z = if flip_coin() then 100 else 200
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


# --- 4. Deeply Nested UDFs and Conditionals ---


def test_conditional_inside_udf_with_stochastic_data(tmp_path):
    script = """
    @iterations=1
    @output=z
    func decide(should_be_random: boolean) -> scalar {
        let s = Normal(100, 10)
        let d = 50
        let choice = if should_be_random then s else d
        return choice * 2
    }
    let z = decide(true)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


def test_deep_udf_chain_feeding_a_stochastic_conditional(tmp_path):
    script = """
    @iterations=1
    @output=final_choice
    func get_trigger() -> scalar { return Bernoulli(0.5) }
    func process_trigger(t: scalar) -> boolean { return t > 0 }
    func decide_from_trigger(b: boolean) -> boolean { return not b }
    let final_choice = if decide_from_trigger(process_trigger(get_trigger())) then 1 else 0
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "final_choice") is not None
