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


# --- 1. Basic Literal and Assignment Tests ---


def test_infer_basic_literals(tmp_path):
    """Tests inference for all basic literal types."""
    script = """
    let my_scalar_int = 10
    let my_scalar_float = -5.5
    let my_string = "hello"
    let my_bool = true
    let my_vector = [1, 2, 3]
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    assert variables["my_scalar_int"]["inferred_type"] == "scalar"
    assert variables["my_scalar_float"]["inferred_type"] == "scalar"
    assert variables["my_string"]["inferred_type"] == "string"
    assert variables["my_bool"]["inferred_type"] == "boolean"
    assert variables["my_vector"]["inferred_type"] == "vector"


def test_infer_from_variable_assignment(tmp_path):
    """Tests that types are correctly propagated through variable assignments."""
    script = """
    let x = 100 # scalar
    let y = x   # should be scalar
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    assert table["global_variables"]["x"]["inferred_type"] == "scalar"
    assert table["global_variables"]["y"]["inferred_type"] == "scalar"


# --- 2. Built-in Function Inference Tests ---


def test_infer_from_builtin_functions(tmp_path):
    """Tests inference from built-in functions with fixed return types."""
    script = """
    let sample = Normal(0, 1) # Normal returns a scalar
    let total = SumVector([1, 2]) # SumVector returns a scalar
    let b = Bernoulli(0.5) # Bernoulli returns a scalar
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    assert variables["sample"]["inferred_type"] == "scalar"
    assert variables["total"]["inferred_type"] == "scalar"
    assert variables["b"]["inferred_type"] == "scalar"


def test_infer_from_dynamic_return_type_functions(tmp_path):
    """Tests inference from functions like 'add' whose return type depends on arguments."""
    script = """
    let s1 = 1
    let s2 = 2
    let v1 = [1, 2]
    
    let r_scalar = s1 + s2          # scalar + scalar -> scalar
    let r_vector1 = v1 + s1         # vector + scalar -> vector
    let r_vector2 = s1 + v1         # scalar + vector -> vector
    let r_vector3 = v1 + v1         # vector + vector -> vector
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    assert variables["r_scalar"]["inferred_type"] == "scalar"
    assert variables["r_vector1"]["inferred_type"] == "vector"
    assert variables["r_vector2"]["inferred_type"] == "vector"
    assert variables["r_vector3"]["inferred_type"] == "vector"


def test_infer_from_multi_return_builtin(tmp_path):
    """Tests inference from a built-in function with a tuple return type."""
    script = """
    let v_asset, v_amort = CapitalizeExpenses(10, [8, 9], 5)
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    # CapitalizeExpenses returns (scalar, scalar)
    assert variables["v_asset"]["inferred_type"] == "scalar"
    assert variables["v_amort"]["inferred_type"] == "scalar"


# --- 3. User-Defined Function (UDF) Inference Tests ---


def test_infer_types_within_udf_body(tmp_path):
    """Tests that types are correctly inferred for local variables inside a UDF."""
    script = """
    func my_func(p1: scalar) -> scalar {
        let local_scalar = p1 * 2
        let local_vector = [1, local_scalar]
        let local_bool = local_scalar > 10
        return local_scalar
    }
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    local_vars = table["user_defined_functions"]["my_func"]["discovered_body"]
    assert local_vars["local_scalar"]["inferred_type"] == "scalar"
    assert local_vars["local_vector"]["inferred_type"] == "vector"
    assert local_vars["local_bool"]["inferred_type"] == "boolean"


def test_infer_type_from_udf_call(tmp_path):
    """Tests inference of a variable assigned the result of a UDF call."""
    script = """
    func get_rate() -> scalar { return 0.05 }
    func get_dims() -> (scalar, scalar) { return (10, 20) }

    let rate = get_rate()
    let w, h = get_dims()
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    assert variables["rate"]["inferred_type"] == "scalar"
    assert variables["w"]["inferred_type"] == "scalar"
    assert variables["h"]["inferred_type"] == "scalar"


# --- 4. Complex and Imported Scenarios ---


def test_infer_type_from_conditional(tmp_path):
    """Tests that the inferred type of an if/else expression is correctly determined."""
    script = """
    let condition = true
    let result = if condition then 100 else 200 # Both branches are scalar
    let str_result = if condition then "A" else "B" # Both branches are string
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    variables = table["global_variables"]
    assert variables["result"]["inferred_type"] == "scalar"
    assert variables["str_result"]["inferred_type"] == "string"


def test_infer_type_from_nested_calls(tmp_path):
    """Tests correct inference through nested function calls."""
    script = """
    let result = SumVector([Normal(0, 1), 10, 20])
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    # SumVector returns a scalar, regardless of the complexity of its arguments
    assert table["global_variables"]["result"]["inferred_type"] == "scalar"


def test_infer_type_from_imported_udf(tmp_path):
    """Tests inference from a UDF defined in another module."""
    module_content = """
    @module
    func get_wacc() -> scalar {
        return 0.08
    }
    """
    main_content = """
    @import "module.vs"
    let wacc = get_wacc()
    """
    create_dummy_file(tmp_path, "module.vs", module_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)
    table = run_inference(main_content, main_path)

    assert table["global_variables"]["wacc"]["inferred_type"] == "scalar"


def test_infer_type_from_deeply_nested_imported_udf(tmp_path):
    """Tests inference through multiple levels of imports."""
    common_content = """
    @module
    func get_risk_free_rate() -> scalar { return 0.02 }
    """
    wacc_content = """
    @module
    @import "common.vs"
    func calculate_wacc() -> scalar {
        let rf = get_risk_free_rate()
        return rf + 0.05
    }
    """
    main_content = """
    @import "wacc.vs"
    let wacc = calculate_wacc()
    """
    create_dummy_file(tmp_path, "common.vs", common_content)
    create_dummy_file(tmp_path, "wacc.vs", wacc_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)
    table = run_inference(main_content, main_path)

    assert table["global_variables"]["wacc"]["inferred_type"] == "scalar"


# --- 5. Edge Cases ---


def test_inference_with_out_of_order_declaration(tmp_path):
    """
    Tests that inference still works when functions are called before they are defined.
    The symbol discovery phase handles finding them first.
    """
    script = """
    let my_val = get_value() # Called before defined

    func get_value() -> scalar {
        return 123
    }
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    assert table["global_variables"]["my_val"]["inferred_type"] == "scalar"


def test_inference_with_undefined_variable_is_any(tmp_path):
    """
    Tests that the inferrer returns 'any' for an undefined variable.
    The validation phase, not the inference phase, is responsible for erroring.
    """
    script = """
    let x = y + 1 # 'y' is not defined
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script)
    table = run_inference(script, file_path)

    # Because y's type is 'any', the result of the addition is also 'any'
    assert table["global_variables"]["x"]["inferred_type"] == "any"
