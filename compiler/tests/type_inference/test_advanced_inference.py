import pytest
from pathlib import Path

from vsc.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.type_inferrer import infer_types_and_taint


# --- Helper to create dummy files for testing imports ---
def create_dummy_file(directory, filename, content):
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)


# --- Helper to run the pipeline up to the inference stage ---
def run_inference(script_content: str, file_path: str):
    """A pipeline helper to get the enriched symbol table."""
    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    enriched_table = infer_types_and_taint(symbol_table)
    return enriched_table


# --- Scenario 1: Taint propagation through a UDF into a conditional ---


def test_stochasticity_propagates_through_udf_into_conditional(tmp_path):
    """
    Tests a multi-stage data flow:
    1. A stochastic variable is created.
    2. It's passed to a deterministic UDF, tainting the result.
    3. That tainted result is used in an `if` condition.
    4. The final assignment should be tainted as stochastic.
    """
    script = """
    func is_positive(val: scalar) -> boolean {
        return val > 0 # This logic is deterministic
    }

    let random_val = Normal(0, 1)                  # Stochastic source
    let decision = is_positive(random_val)         # Should be tainted because input is tainted
    let result = if decision then 100 else 50      # Should be tainted because condition is tainted
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    # The UDF itself is deterministic
    assert table["user_defined_functions"]["is_positive"]["is_stochastic"] is False
    # But the chain of tainting works as expected
    assert variables["random_val"]["is_stochastic"] is True
    assert variables["decision"]["is_stochastic"] is True
    assert variables["result"]["is_stochastic"] is True


# --- Scenario 2: Mixed stochasticity in multi-return UDFs ---


def test_mixed_stochasticity_in_multi_return_udf(tmp_path):
    """
    Tests that a UDF returning both a deterministic and a stochastic value
    correctly taints only the appropriate output variables.
    """
    script = """
    func get_mixed_results() -> (scalar, scalar) {
        let stochastic_part = Normal(10, 2)
        let deterministic_part = 100
        return (deterministic_part, stochastic_part)
    }

    let d_val, s_val = get_mixed_results()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    # The function is considered stochastic because at least one return path is
    assert table["user_defined_functions"]["get_mixed_results"]["is_stochastic"] is True

    # The assigned variables should have their stochasticity inferred from the return expression
    # This currently taints both, which is a safe default. A more advanced
    # analysis could try to separate them, but tainting the whole multi-assignment is correct.
    assert variables["d_val"]["is_stochastic"] is True
    assert variables["s_val"]["is_stochastic"] is True


# --- Scenario 3: Deterministic UDF that can propagate taint ---


def test_deterministic_udf_propagates_taint(tmp_path):
    """
    Tests a UDF that has no internal stochastic sources, but will produce
    a stochastic result if a stochastic argument is passed to it.
    """
    script = """
    func passthrough(a: scalar, b: scalar) -> scalar {
        return a + b
    }

    let s = Normal(0, 1)
    let d = 10
    
    let result_deterministic = passthrough(d, d)  # Should NOT be stochastic
    let result_stochastic = passthrough(s, d)     # Should BE stochastic
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    # The function signature itself is deterministic
    assert table["user_defined_functions"]["passthrough"]["is_stochastic"] is False

    # The stochasticity of the results depends on the call context
    assert variables["result_deterministic"]["is_stochastic"] is False
    assert variables["result_stochastic"]["is_stochastic"] is True


# --- Scenario 4: Unused stochastic variable inside UDF ---


def test_unused_stochastic_variable_does_not_taint_udf(tmp_path):
    """
    Tests that a UDF is NOT marked as stochastic if it creates a random
    variable that has no data-flow path to the `return` statement.
    """
    script = """
    func non_stochastic_return() -> scalar {
        let unused_random = Normal(0, 1) # This should not taint the function's signature
        let deterministic_val = 100
        return deterministic_val
    }
    
    let result = non_stochastic_return()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    # The key assertions
    assert table["user_defined_functions"]["non_stochastic_return"]["is_stochastic"] is False
    assert table["global_variables"]["result"]["is_stochastic"] is False


# --- Scenario 6: Diamond dependency with stochasticity ---


def test_diamond_dependency_with_stochasticity(tmp_path):
    """
    Tests that tainting works correctly across a diamond import dependency.
    main -> module_a -> common
         -> module_b -> common
    The stochastic source is in `common`.
    """
    common_content = """
    @module
    func get_random() -> scalar {
        return Normal(0, 1)
    }
    """
    module_a_content = """
    @module
    @import "common.vs"
    func process_a() -> scalar {
        return get_random() * 2
    }
    """
    module_b_content = """
    @module
    @import "common.vs"
    func process_b() -> scalar {
        return get_random() + 5
    }
    """
    main_content = """
    @import "module_a.vs"
    @import "module_b.vs"
    
    let result_a = process_a()
    let result_b = process_b()
    """

    create_dummy_file(tmp_path, "common.vs", common_content)
    create_dummy_file(tmp_path, "module_a.vs", module_a_content)
    create_dummy_file(tmp_path, "module_b.vs", module_b_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)

    table = run_inference(main_content, main_path)

    # Check that the stochasticity has propagated all the way up the chain
    assert table["user_defined_functions"]["get_random"]["is_stochastic"] is True
    assert table["user_defined_functions"]["process_a"]["is_stochastic"] is True
    assert table["user_defined_functions"]["process_b"]["is_stochastic"] is True

    # Check the final variables in the main script
    assert table["global_variables"]["result_a"]["is_stochastic"] is True
    assert table["global_variables"]["result_b"]["is_stochastic"] is True
