import pytest
from pathlib import Path

from vsc.parser.parser import parse_valuascript
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


# --- 1. Basic Tainting from Stochastic Sources ---


@pytest.mark.parametrize("stochastic_func", ["Normal(0, 1)", "Lognormal(0, 1)", "Beta(1, 1)", "Uniform(0, 1)", "Bernoulli(0.5)", "Pert(1, 2, 3)", "Triangular(1, 2, 3)"])
def test_taint_from_direct_stochastic_source(tmp_path, stochastic_func):
    """Tests that a variable is tainted if assigned directly from any stochastic function."""
    script = f"let random_var = {stochastic_func}"
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)
    assert table["global_variables"]["random_var"]["is_stochastic"] is True


def test_no_taint_for_deterministic_script(tmp_path):
    """Ensures a fully deterministic script has no stochastic variables."""
    script = """
    let x = 10
    let y = x * 2
    let z = [x, y]
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)
    assert table["global_variables"]["x"]["is_stochastic"] is False
    assert table["global_variables"]["y"]["is_stochastic"] is False
    assert table["global_variables"]["z"]["is_stochastic"] is False


# --- 2. Propagation of Taint ---


def test_taint_propagates_through_assignments(tmp_path):
    """If x is stochastic, y = x must make y stochastic."""
    script = """
    let x = Normal(0, 1) # Stochastic
    let y = x              # Should be tainted
    let z = 100            # Should NOT be tainted
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)
    assert table["global_variables"]["x"]["is_stochastic"] is True
    assert table["global_variables"]["y"]["is_stochastic"] is True
    assert table["global_variables"]["z"]["is_stochastic"] is False


def test_taint_propagates_through_expressions(tmp_path):
    """If any part of an expression is stochastic, the result is tainted."""
    script = """
    let s = Normal(0, 1) # Stochastic
    let d = 10           # Deterministic
    
    let r1 = s + d       # Tainted
    let r2 = d * d       # Not tainted
    let r3 = s / s       # Tainted
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)
    assert table["global_variables"]["r1"]["is_stochastic"] is True
    assert table["global_variables"]["r2"]["is_stochastic"] is False
    assert table["global_variables"]["r3"]["is_stochastic"] is True


def test_taint_propagates_through_conditionals(tmp_path):
    """If either the 'then' or 'else' branch is stochastic, the result is tainted."""
    script = """
    let s = Normal(0, 1)
    let d = 10
    let cond = true

    let r1 = if cond then s else d # Tainted (then branch)
    let r2 = if cond then d else s # Tainted (else branch)
    let r3 = if cond then d else d # Not tainted
    let r4 = if s > 0 then d else d # The condition being stochastic makes the value trial-dependent. This IS stochastic.
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)
    assert table["global_variables"]["r1"]["is_stochastic"] is True
    assert table["global_variables"]["r2"]["is_stochastic"] is True
    assert table["global_variables"]["r3"]["is_stochastic"] is False
    assert table["global_variables"]["r4"]["is_stochastic"] is True


# --- 3. User-Defined Function (UDF) Tainting Scenarios ---


def test_udf_is_tainted_by_internal_source(tmp_path):
    """A UDF becomes stochastic if it uses a stochastic function in its body."""
    script = """
    func get_random_growth() -> scalar {
        let g = Uniform(0.01, 0.05) # Internal stochastic source
        return g
    }
    let growth = get_random_growth() # Should be tainted
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    # Check that the function itself is marked as stochastic
    assert table["user_defined_functions"]["get_random_growth"]["is_stochastic"] is True
    # Check that the variable assigned its result is also tainted
    assert table["global_variables"]["growth"]["is_stochastic"] is True


def test_taint_propagates_through_udf_argument(tmp_path):
    """A deterministic UDF produces a stochastic result if called with a stochastic argument."""
    script = """
    func add_margin(revenue: scalar) -> scalar {
        return revenue * 1.1 # Deterministic logic
    }
    
    let random_revenue = Normal(1000, 200) # Stochastic source
    let projected_revenue = add_margin(random_revenue) # Should be tainted
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    # The function itself is NOT stochastic
    print(table["user_defined_functions"]["add_margin"] )
    assert table["user_defined_functions"]["add_margin"]["is_stochastic"] is False
    # But the result of this specific call IS stochastic
    assert table["global_variables"]["projected_revenue"]["is_stochastic"] is True


def test_taint_propagates_through_multi_assignment_udf(tmp_path):
    """If a multi-return UDF is stochastic, all result variables are tainted."""
    script = """
    func get_stochastic_sales() -> (scalar, scalar) {
        let units = Normal(100, 10)
        let price = 50 # Deterministic part
        return (units * price, units)
    }
    let revenue, units_sold = get_stochastic_sales()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    assert table["user_defined_functions"]["get_stochastic_sales"]["is_stochastic"] is True
    assert table["global_variables"]["revenue"]["is_stochastic"] is True
    assert table["global_variables"]["units_sold"]["is_stochastic"] is True


# --- 4. Tainting Across Imported Modules ---


def test_taint_from_imported_stochastic_udf(tmp_path):
    """Tests tainting from a UDF that is stochastic and imported."""
    module_content = """
    @module
    func get_random_cagr() -> scalar {
        return Pert(0.02, 0.03, 0.04)
    }
    """
    main_content = """
    @import "module.vs"
    let cagr = get_random_cagr()
    """
    create_dummy_file(tmp_path, "module.vs", module_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)
    table = run_inference(main_content, main_path)

    # The imported function should be correctly identified as stochastic
    assert table["user_defined_functions"]["get_random_cagr"]["is_stochastic"] is True
    # The result in the main file should be tainted
    assert table["global_variables"]["cagr"]["is_stochastic"] is True


def test_taint_propagates_through_imported_deterministic_udf(tmp_path):
    """Tests tainting when passing a stochastic variable to an imported deterministic UDF."""
    module_content = """
    @module
    func apply_tax(ebit: scalar) -> scalar {
        return ebit * 0.75
    }
    """
    main_content = """
    @import "module.vs"
    let random_ebit = Normal(100, 10)
    let ebit_after_tax = apply_tax(random_ebit)
    """
    create_dummy_file(tmp_path, "module.vs", module_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)
    table = run_inference(main_content, main_path)

    assert table["user_defined_functions"]["apply_tax"]["is_stochastic"] is False
    assert table["global_variables"]["ebit_after_tax"]["is_stochastic"] is True


def test_taint_propagates_through_deeply_nested_imports(tmp_path):
    """
    main -> module_a -> module_b
    module_b contains the stochastic source.
    """
    module_b_content = """
    @module
    func get_shock() -> scalar { return Normal(0, 1) }
    """
    module_a_content = """
    @module
    @import "module_b.vs"
    func apply_shock(value: scalar) -> scalar {
        return value + get_shock()
    }
    """
    main_content = """
    @import "module_a.vs"
    let final_value = apply_shock(100)
    """
    create_dummy_file(tmp_path, "module_b.vs", module_b_content)
    create_dummy_file(tmp_path, "module_a.vs", module_a_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)
    table = run_inference(main_content, main_path)

    # Check the whole chain
    assert table["user_defined_functions"]["get_shock"]["is_stochastic"] is True
    assert table["user_defined_functions"]["apply_shock"]["is_stochastic"] is True
    assert table["global_variables"]["final_value"]["is_stochastic"] is True
