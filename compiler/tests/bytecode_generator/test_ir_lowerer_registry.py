import pytest
from typing import Dict, Any

# The module we are testing
from vsc.bytecode_generation.ir_lowerer import IRLowerer


@pytest.fixture
def base_registries() -> Dict[str, Any]:
    """Provides a clean, boilerplate registry object for tests."""
    return {
        "variable_registries": {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []},
        "variable_map": {},
    }


def test_registry_after_simple_scalar_lift(base_registries):
    """
    Tests that a single lifted scalar temporary is correctly added to the registries.
    """
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["x", "result"])
    registries["variable_map"]["x"] = {"type": "SCALAR", "index": 0}
    registries["variable_map"]["result"] = {"type": "SCALAR", "index": 1}

    partitioned_ir = {"per_trial_steps": [{"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["x", {"function": "Normal", "args": [0, 1]}]}]}
    model = {"all_signatures": {"Normal": {"return_type": "scalar"}}}

    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model)
    _, updated_registries = lowerer.lower()

    # ASSERT
    # Check the variable_registries
    assert "__temp_lifted_1" in updated_registries["variable_registries"]["SCALAR"]
    assert len(updated_registries["variable_registries"]["SCALAR"]) == 3

    # Check the variable_map
    temp_var_info = updated_registries["variable_map"].get("__temp_lifted_1")
    assert temp_var_info is not None
    assert temp_var_info["type"] == "SCALAR"
    assert temp_var_info["index"] == 2  # Should be the next available scalar index


def test_registry_after_multi_return_lift(base_registries):
    """
    Tests that temporary variables from a multi-return function are all
    correctly added to the registries with sequential indices.
    """
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["VECTOR"].extend(["sir1", "sir2", "sir3"])
    registries["variable_map"]["sir1"] = {"type": "VECTOR", "index": 0}
    registries["variable_map"]["sir2"] = {"type": "VECTOR", "index": 1}
    registries["variable_map"]["sir3"] = {"type": "VECTOR", "index": 2}

    partitioned_ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["sir1", "sir2", "sir3"], "function": "identity", "args": [{"function": "get_sir", "args": []}]}]}
    model = {"all_signatures": {"get_sir": {"return_type": ["vector", "vector", "vector"]}}}

    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model)
    _, updated_registries = lowerer.lower()

    # ASSERT
    vec_registry = updated_registries["variable_registries"]["VECTOR"]
    var_map = updated_registries["variable_map"]

    assert "__temp_lifted_1" in vec_registry
    assert "__temp_lifted_2" in vec_registry
    assert "__temp_lifted_3" in vec_registry
    assert len(vec_registry) == 6

    # Check the variable_map entries for all three new variables
    assert var_map["__temp_lifted_1"] == {"type": "VECTOR", "index": 3}
    assert var_map["__temp_lifted_2"] == {"type": "VECTOR", "index": 4}
    assert var_map["__temp_lifted_3"] == {"type": "VECTOR", "index": 5}


def test_registry_after_mixed_type_lifting(base_registries):
    """
    Tests that lifting functions with different return types correctly populates
    the different typed lists within the registries.
    """
    # ARRANGE
    registries = base_registries
    registries["variable_registries"]["SCALAR"].extend(["result"])
    registries["variable_map"]["result"] = {"type": "SCALAR", "index": 0}

    model = {"all_signatures": {"is_ready": {"return_type": "boolean"}, "create_data": {"return_type": "vector"}, "process_data": {"return_type": "scalar"}}}
    partitioned_ir = {
        "pre_trial_steps": [
            {
                "type": "conditional_assignment",
                "result": ["result"],
                "condition": {"function": "is_ready", "args": []},
                "then_expr": {"function": "process_data", "args": [{"function": "create_data", "args": []}]},
                "else_expr": -1.0,
            }
        ],
    }

    # ACT
    lowerer = IRLowerer(partitioned_ir, registries, model)
    _, updated_registries = lowerer.lower()

    # ASSERT
    var_map = updated_registries["variable_map"]

    # Check that each temporary variable landed in the correct typed registry
    assert "__temp_lifted_1" in updated_registries["variable_registries"]["BOOLEAN"]
    assert "__temp_lifted_2" in updated_registries["variable_registries"]["VECTOR"]
    assert "__temp_lifted_3" in updated_registries["variable_registries"]["SCALAR"]

    # Check that their indices are correct WITHIN their own type
    assert var_map["__temp_lifted_1"] == {"type": "BOOLEAN", "index": 0}  # First boolean
    assert var_map["__temp_lifted_2"] == {"type": "VECTOR", "index": 0}  # First vector
    assert var_map["__temp_lifted_3"] == {"type": "SCALAR", "index": 1}  # Second scalar
