import pytest
import copy
from typing import Dict, Any

# The module we are testing
from vsc.bytecode_generation.ir_lowerer import IRLowerer


@pytest.fixture
def base_model_for_mutation() -> Dict[str, Any]:
    """Provides a model that will trigger the creation of temp variables."""
    return {
        "global_variables": {
            "x": {"inferred_type": "scalar"},
            "result": {"inferred_type": "scalar"},
        },
        "all_signatures": {
            "Normal": {"return_type": "scalar", "is_stochastic": True},
            "add": {"return_type": lambda types: "scalar", "is_stochastic": False},
        },
    }


def test_lowerer_modifies_model_in_place(base_model_for_mutation):
    """
    This test proves that the IRLowerer mutates the model object it receives
    by adding new temporary variables to its 'global_variables' dictionary.
    """
    # ARRANGE
    model = base_model_for_mutation
    partitioned_ir = {"per_trial_steps": [{"type": "execution_assignment", "result": ["result"], "function": "add", "args": ["x", {"function": "Normal", "args": [0, 1]}]}]}

    # Create a deep copy of the original model to preserve its "before" state.
    model_before = copy.deepcopy(model)

    # ACT
    lowerer = IRLowerer(partitioned_ir, model)
    _, model_after = lowerer.lower()

    # ASSERT

    # 1. The object ID should be the same, proving it was an in-place modification.
    assert id(model) == id(model_after)

    # 2. The content of the model BEFORE the call should be different from AFTER.
    assert model_before != model_after

    # 3. The specific change we expect is the addition of a new temporary variable.
    assert "__temp_lifted_1" not in model_before["global_variables"]
    assert "__temp_lifted_1" in model_after["global_variables"]

    # 4. Check the metadata of the new temporary variable.
    temp_var_info = model_after["global_variables"]["__temp_lifted_1"]
    assert temp_var_info["inferred_type"] == "scalar"
    assert temp_var_info["is_stochastic"] is True
