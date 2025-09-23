import pytest
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Optional

# --- Test Dependencies ---
from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint
from vsc.semantic_validator import validate_semantics
from vsc.ir_generator import generate_ir
from vsc.optimizer.copy_propagation import run_copy_propagation
from vsc.optimizer.tuple_forwarding import run_tuple_forwarding
from vsc.optimizer.alias_resolver import run_alias_resolver
from vsc.optimizer.constant_folding import run_constant_folding
from vsc.optimizer.dead_code_elimination import run_dce
from vsc.ir_partitioner import partition_ir  # The module we are testing

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


# --- 1. Basic Tainting and Partitioning ---


def test_fully_deterministic_script_has_empty_per_trial_block(tmp_path):
    script = """
    @iterations=1
    @output=c
    let a = 10
    let b = a * 2
    let c = b + 5
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) > 0
    assert len(partitioned["per_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "c") is not None


def test_simple_stochastic_variable_moves_to_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=z
    let d_vec = GrowSerie(100, 0, 1) # Deterministic, but won't be folded
    let d = d_vec[0]
    let s = Normal(0, 1)              # Stochastic
    let z = d + s                     # Keeps 'd' alive
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)

    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d_vec") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "s") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


def test_taint_propagation_moves_dependent_steps_to_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=d
    let s = Normal(0, 1)
    let d = s + 10
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert len(partitioned["per_trial_steps"]) >= 1
    assert _get_step_for_variable(partitioned["per_trial_steps"], "d") is not None


# --- 2. Conditionals and Logical Operators ---


def test_conditional_with_stochastic_branch_is_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=z
    let s = Normal(0, 1)
    let d_vec = GrowSerie(10, 0, 1)
    let d = d_vec[0]
    let cond = d > 5
    let z = if cond then s else d
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)

    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d_vec") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "d") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "cond") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "s") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


def test_conditional_with_stochastic_condition_is_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=z
    let s_cond = Normal(0, 1) > 0
    let z = if s_cond then 100 else 200
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "s_cond") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


def test_logical_operator_with_stochastic_operand_is_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=z
    let s_bool = Bernoulli(0.5) > 0
    let d_bool = true
    let z = s_bool and d_bool
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "s_bool") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


# --- 3. User-Defined Function (UDF) Scenarios ---


def test_udf_with_internal_stochastic_source_is_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=x
    func get_random_value() -> scalar { return Normal(10, 2) * 5 }
    let x = get_random_value()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "x") is not None


def test_passing_stochastic_argument_to_udf_makes_call_per_trial(tmp_path):
    script = """
    @iterations=1
    @output=y
    func add_margin(revenue: scalar) -> scalar { return revenue * 1.2 }
    let s_revenue = Normal(1000, 100)
    let y = add_margin(s_revenue)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "s_revenue") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "y") is not None


def test_nested_udf_calls_propagate_stochasticity_correctly(tmp_path):
    script = """
    @iterations=1
    @output=z
    func get_stochastic_base() -> scalar { return Normal(10, 1) }
    func process_base(base: scalar) -> scalar { return base + 100 }
    let z = process_base(get_stochastic_base())
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    partitioned = run_full_pipeline_to_partitioned_ir(script, file_path)
    assert len(partitioned["pre_trial_steps"]) == 0
    assert _get_step_for_variable(partitioned["per_trial_steps"], "z") is not None


# --- 4. Import Scenarios ---


def test_importing_a_stochastic_udf(tmp_path):
    module_content = """
    @module
    func get_market_shock() -> scalar { return Normal(0, 0.05) }
    """
    main_content = """
    @iterations=1
    @output=y
    @import "module.vs"
    let br_vec = GrowSerie(0.07, 0, 1)
    let base_return = br_vec[0]
    let y = base_return + get_market_shock()
    """
    create_dummy_file(tmp_path, "module.vs", module_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)
    partitioned = run_full_pipeline_to_partitioned_ir(main_content, main_path)

    assert _get_step_for_variable(partitioned["pre_trial_steps"], "br_vec") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "base_return") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "y") is not None


def test_deeply_nested_imports_propagate_stochasticity(tmp_path):
    source_content = "@module\nfunc get_rand() -> scalar { return Lognormal(0.05, 0.1) }"
    p2_content = """@module\n@import "source.vs"\nfunc p2(b:scalar) -> scalar { return b * get_rand() }"""
    main_content = """
    @iterations=1
    @output=final_value
    @import "p2.vs"
    let sv_vec = GrowSerie(1000, 0, 1)
    let start_value = sv_vec[0]
    let final_value = p2(start_value)
    """
    create_dummy_file(tmp_path, "source.vs", source_content)
    create_dummy_file(tmp_path, "p2.vs", p2_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)

    partitioned = run_full_pipeline_to_partitioned_ir(main_content, main_path)

    assert _get_step_for_variable(partitioned["pre_trial_steps"], "sv_vec") is not None
    assert _get_step_for_variable(partitioned["pre_trial_steps"], "start_value") is not None
    assert _get_step_for_variable(partitioned["per_trial_steps"], "final_value") is not None
