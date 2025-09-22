import pytest
import json
from pathlib import Path
from typing import Dict, Any

# The module we are testing
from vsc.bytecode_generation.resource_allocator import ResourceAllocator

# --- Test Helpers ---

# Define the path to our permanent golden files directory, relative to this test file.
GOLDEN_FILES_DIR = Path(__file__).parent / "golden_files"


def load_golden_file(file_path: Path) -> Dict[str, Any]:
    """Helper to load a JSON file for testing."""
    if not file_path.exists():
        pytest.fail(f"Golden file not found: {file_path}. " f"Please run the compiler with flags -c 4, -c 7, and -c 8a to generate it.")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- The Golden File Regression Test ---


def test_resource_allocator_against_golden_file_contract():
    """
    This is a high-level regression test that acts as a safety net.

    It loads a pre-generated, complex IR and model from the 'golden_files'
    directory and compares the allocator's output to a known "golden" result
    that has been manually verified and committed to the repository.

    This ensures that the allocator's behavior remains stable and correct
    for a realistic, complex program, and it is completely isolated from
    changes in the upstream optimizer or parser.
    """
    # --- 1. Load the golden input and expected output files ---
    model = load_golden_file(GOLDEN_FILES_DIR / "model_stage_4.json")
    partitioned_ir = load_golden_file(GOLDEN_FILES_DIR / "model_stage_7.json")
    expected_result = load_golden_file(GOLDEN_FILES_DIR / "expected_model_stage_8a.json")

    # --- 2. Run the unit under test ---
    allocator = ResourceAllocator(partitioned_ir, model)
    actual_result = allocator.allocate()

    # --- 3. Assert that the actual output matches the contract ---
    assert actual_result == expected_result


# --- 2. Focused Unit Tests ---


def test_allocates_basic_variable_types():
    """Tests correct partitioning of variables into typed registries."""
    model = {
        "global_variables": {
            "s1": {"inferred_type": "scalar"},
            "s2": {"inferred_type": "scalar"},
            "v1": {"inferred_type": "vector"},
            "b1": {"inferred_type": "boolean"},
            "str1": {"inferred_type": "string"},
        },
        "user_defined_functions": {},  # Add empty UDF dict for completeness
    }
    ir = {
        "pre_trial_steps": [
            {"type": "literal_assignment", "result": ["s1"], "value": 1},
            {"type": "literal_assignment", "result": ["v1"], "value": [1, 2]},
            {"type": "literal_assignment", "result": ["b1"], "value": True},
            {"type": "literal_assignment", "result": ["s2"], "value": 2},
            {"type": "literal_assignment", "result": ["str1"], "value": "test"},
        ]
    }

    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    assert result["variable_registries"]["SCALAR"] == ["s1", "s2"]
    assert result["variable_map"]["s1"] == {"type": "SCALAR", "index": 0}
    assert result["variable_map"]["s2"] == {"type": "SCALAR", "index": 1}

def test_handles_mangled_and_temporary_variables():
    """Tests correct type resolution for mangled and temp variables."""
    model = {"user_defined_functions": {"my_func": {"discovered_body": {"local_vec": {"inferred_type": "vector"}}}}, "global_variables": {}}
    ir = {"pre_trial_steps": [{"type": "literal_assignment", "result": ["__my_func_1__local_vec"], "value": [1]}, {"type": "literal_assignment", "result": ["__temp_1"], "value": 123}]}
    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    assert result["variable_registries"]["VECTOR"] == ["__my_func_1__local_vec"]
    assert result["variable_registries"]["SCALAR"] == ["__temp_1"]


def test_handles_empty_ir():
    """Tests that an empty IR input produces valid empty registries."""
    model = {"global_variables": {}, "user_defined_functions": {}}
    ir = {"pre_trial_steps": [], "per_trial_steps": []}

    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    assert result["variable_registries"] == {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []}
    assert result["variable_map"] == {}


def test_scalars_in_constant_vector_are_not_added_to_scalar_pool():
    """Ensures scalars inside a constant vector are not double-counted."""
    model = {"global_variables": {"v": {"inferred_type": "vector"}, "s": {"inferred_type": "scalar"}}, "user_defined_functions": {}}
    ir = {
        "pre_trial_steps": [
            {"type": "literal_assignment", "result": ["v"], "value": [10.0, 20.0]},
            {"type": "literal_assignment", "result": ["s"], "value": 10.0},
        ]
    }
    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    assert result["constant_pools"]["VECTOR"] == [[10.0, 20.0]]
    assert result["constant_pools"]["SCALAR"] == [10.0]
