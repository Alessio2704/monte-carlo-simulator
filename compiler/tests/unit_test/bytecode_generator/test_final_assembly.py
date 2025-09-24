import pytest
from typing import Dict, Any

# The class we are testing
from vsc.bytecode_generator import BytecodeGenerator
from vsc.parser import _StringLiteral

# --- Fixtures ---


@pytest.fixture
def base_model_for_assembly() -> Dict[str, Any]:
    """Provides a base model structure needed by the BytecodeGenerator."""
    main_file_path = "/path/to/main.vs"
    return {
        "main_file_path": main_file_path,
        "processed_asts": {
            main_file_path: {
                "directives": [],  # Directives will be added by each test
            }
        },
        # Other parts of the model can be empty for these tests
        "user_defined_functions": {},
        "global_variables": {},
    }


@pytest.fixture
def populated_generator(base_model_for_assembly) -> BytecodeGenerator:
    """
    Creates a BytecodeGenerator instance with its internal state (registries, emitted_code)
    pre-populated, as if the preceding phases (8a, 8b, 8c) had already run.
    """
    # Dummy IR and model are sufficient, as we are only testing the final assembly step.
    partitioned_ir = {"pre_trial_steps": [], "per_trial_steps": []}

    # Initialize the generator
    generator = BytecodeGenerator(partitioned_ir, base_model_for_assembly)

    # Manually set the state that would have been created by previous phases
    generator.registries = {
        "variable_registries": {
            "SCALAR": ["s1", "s2", "s3"],
            "VECTOR": ["v1"],
            "BOOLEAN": [],
            "STRING": ["str1"],
        },
        "constant_pools": {"SCALAR": [1.0, 2.0]},
    }

    generator.emitted_code = {
        "pre_trial_instructions": [{"op": 0}],
        "per_trial_instructions": [{"op": 1}],
    }

    return generator


# --- Test Cases ---


def test_final_assembly_with_full_config(populated_generator):
    """
    Tests that the final recipe is correctly assembled when all relevant
    directives are present in the model.
    """
    # ARRANGE
    # Add directives to the model that the generator will use
    populated_generator.model["processed_asts"][populated_generator.model["main_file_path"]]["directives"] = [
        {"name": "iterations", "value": 50000},
        {"name": "output", "value": "final_result"},
        {"name": "output_file", "value": _StringLiteral("output/results.csv")},
    ]

    # ACT
    recipe = populated_generator.run_final_assembly()

    # ASSERT
    # 1. Check for the presence of all top-level keys
    assert "simulation_config" in recipe
    assert "variable_register_counts" in recipe
    assert "constants" in recipe
    assert "pre_trial_instructions" in recipe
    assert "per_trial_instructions" in recipe

    # 2. Deeply check the simulation_config structure and values
    config = recipe["simulation_config"]
    assert config["num_trials"] == 50000
    assert config["output_variable"] == "final_result"
    assert config["output_file"] == "output/results.csv"


def test_final_assembly_with_minimal_config(populated_generator):
    """
    Tests that the recipe is correct when optional directives (like @output_file)
    are missing.
    """
    # ARRANGE
    populated_generator.model["processed_asts"][populated_generator.model["main_file_path"]]["directives"] = [
        {"name": "iterations", "value": 100},
        {"name": "output", "value": "some_var"},
    ]

    # ACT
    recipe = populated_generator.run_final_assembly()

    # ASSERT
    config = recipe["simulation_config"]
    assert config["num_trials"] == 100
    assert config["output_variable"] == "some_var"
    assert config["output_file"] is None  # Should be None or null in JSON


def test_variable_register_counts_are_correct(populated_generator):
    """
    Tests that the `variable_register_counts` in the final recipe accurately
    reflect the contents of the registries artifact.
    """
    # ARRANGE
    # The populated_generator fixture already sets up the registries with specific counts.
    # Just need to add the minimal directives for the assembly to run.
    populated_generator.model["processed_asts"][populated_generator.model["main_file_path"]]["directives"] = [
        {"name": "iterations", "value": 1},
        {"name": "output", "value": "s1"},
    ]

    # ACT
    recipe = populated_generator.run_final_assembly()

    # ASSERT
    counts = recipe["variable_register_counts"]
    assert counts["SCALAR"] == 3  # From ["s1", "s2", "s3"] in the fixture
    assert counts["VECTOR"] == 1  # From ["v1"]
    assert counts["BOOLEAN"] == 0  # From []
    assert counts["STRING"] == 1  # From ["str1"]


def test_assembly_handles_empty_registries_and_instructions(base_model_for_assembly):
    """
    An edge case test to ensure assembly doesn't crash if prior phases
    produced empty results (e.g., a script with only constant calculations
    that get optimized away).
    """
    # ARRANGE
    # A generator with empty internal state
    generator = BytecodeGenerator({"pre_trial_steps": [], "per_trial_steps": []}, base_model_for_assembly)
    generator.registries = {"variable_registries": {}, "constant_pools": {}}
    generator.emitted_code = {"pre_trial_instructions": [], "per_trial_instructions": []}

    # Add minimal directives
    generator.model["processed_asts"][generator.model["main_file_path"]]["directives"] = [
        {"name": "iterations", "value": 1},
        {"name": "output", "value": "x"},
    ]

    # ACT
    recipe = generator.run_final_assembly()

    # ASSERT
    # Check that the structure is still valid but the counts and lists are empty
    counts = recipe["variable_register_counts"]
    assert counts["SCALAR"] == 0
    assert counts["VECTOR"] == 0
    assert counts["BOOLEAN"] == 0
    assert counts["STRING"] == 0

    assert recipe["constants"] == {}
    assert recipe["pre_trial_instructions"] == []
    assert recipe["per_trial_instructions"] == []
