import pytest
from typing import Dict, Any

# The module we are testing
from vsc.bytecode_generation.ir_lowerer import IRLowerer


@pytest.fixture
def base_model() -> Dict[str, Any]:
    """Provides a clean, boilerplate model object for tests."""
    return {
        "global_variables": {},
        "all_signatures": {},
    }


def test_registry_after_simple_scalar_lift(base_model):
    """
    Tests that a single lifted scalar temporary is correctly added to the model.
    """
    # ARRANGE
    model = base_model
    model["global_variables"] = {
        "x": {"inferred_type": "scalar", "is_stochastic": False},
        "result": {"inferred_type": "scalar", "is_stochastic": True},
    }
    model["all_signatures"]["Normal"] = {"return_type": "scalar", "is_stochastic": True}
    model["all_signatures"]["add"] = {"return_type": "scalar", "is_stochastic": False}

    partitioned_ir = {"per_trial_steps": [{"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["x", {"function": "Normal", "args": [0, 1]}]}]}

    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    _, updated_model = lowerer.lower()

    # ASSERT
    temp_var_info = updated_model["global_variables"].get("__temp_lifted_1")
    assert temp_var_info is not None
    assert temp_var_info["inferred_type"] == "scalar"
    assert temp_var_info["is_stochastic"] is True


def test_registry_after_multi_return_lift(base_model):
    """
    Tests that temporary variables from a multi-return function are all
    correctly added to the model.
    """
    # ARRANGE
    model = base_model
    model["global_variables"] = {
        "sir1": {"inferred_type": "vector", "is_stochastic": False},
        "sir2": {"inferred_type": "vector", "is_stochastic": False},
        "sir3": {"inferred_type": "vector", "is_stochastic": False},
    }
    # This identity is a placeholder for a complex multi-return call
    model["all_signatures"]["identity"] = {"return_type": lambda types: types[0]}
    model["all_signatures"]["get_sir"] = {"return_type": ["vector", "vector", "vector"], "is_stochastic": False}

    partitioned_ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["sir1", "sir2", "sir3"], "function": "identity", "args": [{"function": "get_sir", "args": []}]}]}

    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    _, updated_model = lowerer.lower()

    # ASSERT
    global_vars = updated_model["global_variables"]
    temp1 = global_vars.get("__temp_lifted_1")
    temp2 = global_vars.get("__temp_lifted_2")
    temp3 = global_vars.get("__temp_lifted_3")

    assert temp1 is not None and temp1["inferred_type"] == "vector"
    assert temp2 is not None and temp2["inferred_type"] == "vector"
    assert temp3 is not None and temp3["inferred_type"] == "vector"


def test_registry_after_mixed_type_lifting(base_model):
    """
    Tests that lifting functions with different return types correctly populates
    the model with correctly typed temporary variables.
    """
    # ARRANGE
    model = base_model
    model["global_variables"]["result"] = {"inferred_type": "scalar"}
    model["all_signatures"] = {
        "is_ready": {"return_type": "boolean", "is_stochastic": False},
        "create_data": {"return_type": "vector", "is_stochastic": False},
        "process_data": {"return_type": "scalar", "is_stochastic": False},
    }
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
    lowerer = IRLowerer(partitioned_ir, model)
    _, updated_model = lowerer.lower()

    # ASSERT
    global_vars = updated_model["global_variables"]
    temp1 = global_vars.get("__temp_lifted_1")  # is_ready() -> boolean
    temp2 = global_vars.get("__temp_lifted_2")  # create_data() -> vector
    temp3 = global_vars.get("__temp_lifted_3")  # process_data() -> scalar

    assert temp1 is not None and temp1["inferred_type"] == "boolean"
    assert temp2 is not None and temp2["inferred_type"] == "vector"
    assert temp3 is not None and temp3["inferred_type"] == "scalar"
