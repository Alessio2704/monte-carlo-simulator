import pytest
import json
from pathlib import Path
from typing import Dict, Any

# The modules we are testing
from vsc.bytecode_generation.resource_allocator import ResourceAllocator
from vsc.bytecode_generation.ir_lowerer import IRLowerer
from vsc.parser import _StringLiteral
from vsc.utils import compiler_artifact_decoder_hook
from vsc.exceptions import ValuaScriptError, InternalCompilerError


# --- 1. Focused Unit Tests ---


def test_deduplicates_constants_correctly():
    """Tests that identical constants are stored only once."""
    model = {
        "global_variables": {
            "x": {"inferred_type": "scalar"},
            "y": {"inferred_type": "vector"},
            "z": {"inferred_type": "string"},
            "w": {"inferred_type": "string"},
        },
        "user_defined_functions": {},
    }
    ir = {
        "pre_trial_steps": [
            {"type": "execution_assignment", "result": ["x"], "args": [10.5, 20.0, 10.5]},
            # Use _StringLiteral to match what the IR generator produces
            {"type": "literal_assignment", "result": ["z"], "value": _StringLiteral("hello")},
            {"type": "literal_assignment", "result": ["w"], "value": _StringLiteral("hello")},
        ]
    }

    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    assert result["constant_pools"]["SCALAR"] == [10.5, 20.0]
    assert result["constant_pools"]["BOOLEAN"] == []
    assert result["constant_pools"]["VECTOR"] == []
    assert result["constant_pools"]["STRING"] == ["hello"]


def test_ignores_non_constant_vectors_and_identity_tuples():
    """Regression test to ensure lists of variables are not treated as constants."""
    model = {
        "global_variables": {
            "a": {"inferred_type": "scalar"},
            "b": {"inferred_type": "scalar"},
            "d": {"inferred_type": "scalar"},
            "e": {"inferred_type": "scalar"},
        },
        "user_defined_functions": {},
    }
    ir = {"pre_trial_steps": [{"type": "execution_assignment", "result": ["d", "e"], "function": "identity", "args": [["a", "b"]]}]}

    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    assert result["constant_pools"]["VECTOR"] == []
    # Check that d and e were still allocated correctly
    assert result["variable_registries"]["SCALAR"] == ["d", "e"]
    assert result["variable_map"]["d"]["index"] == 0
    assert result["variable_map"]["e"]["index"] == 1


# --- All other tests remain the same as they were already correct ---
def test_allocates_basic_variable_types():
    model = {
        "global_variables": {
            "s1": {"inferred_type": "scalar"},
            "s2": {"inferred_type": "scalar"},
            "v1": {"inferred_type": "vector"},
            "b1": {"inferred_type": "boolean"},
            "str1": {"inferred_type": "string"},
        },
        "user_defined_functions": {},
    }
    ir = {
        "pre_trial_steps": [
            {"type": "literal_assignment", "result": ["s1"], "value": 1},
            {"type": "literal_assignment", "result": ["v1"], "value": [1, 2]},
            {"type": "literal_assignment", "result": ["b1"], "value": True},
            {"type": "literal_assignment", "result": ["s2"], "value": 2},
            {"type": "literal_assignment", "result": ["str1"], "value": _StringLiteral("test")},
        ]
    }
    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()
    assert result["variable_registries"]["SCALAR"] == ["s1", "s2"]
    assert result["variable_map"]["s1"] == {"type": "SCALAR", "index": 0}
    assert result["variable_map"]["s2"] == {"type": "SCALAR", "index": 1}


def test_handles_mangled_and_temporary_variables():
    model = {
        "user_defined_functions": {"my_func": {"discovered_body": {"local_vec": {"inferred_type": "vector"}}}},
        "global_variables": {"__temp_1": {"inferred_type": "scalar"}},
    }
    ir = {"pre_trial_steps": [{"type": "literal_assignment", "result": ["__my_func_1__local_vec"], "value": [1]}, {"type": "literal_assignment", "result": ["__temp_1"], "value": 123}]}
    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()
    assert result["variable_registries"]["VECTOR"] == ["__my_func_1__local_vec"]
    assert result["variable_registries"]["SCALAR"] == ["__temp_1"]


def test_handles_empty_ir():
    model = {"global_variables": {}, "user_defined_functions": {}}
    ir = {"pre_trial_steps": [], "per_trial_steps": []}
    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()
    assert result["variable_registries"] == {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []}
    assert result["variable_map"] == {}


def test_scalars_in_constant_vector_are_not_added_to_scalar_pool():
    model = {"global_variables": {"v": {"inferred_type": "vector"}, "s": {"inferred_type": "scalar"}}, "user_defined_functions": {}}
    ir = {"pre_trial_steps": [{"type": "literal_assignment", "result": ["v"], "value": [10.0, 20.0]}, {"type": "literal_assignment", "result": ["s"], "value": 10.0}]}
    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()
    assert result["constant_pools"]["VECTOR"] == [[10.0, 20.0]]
    assert result["constant_pools"]["SCALAR"] == [10.0]


def test_finds_constants_in_all_parts_of_conditionals():
    """
    Ensures the allocator scans the `condition`, `then_expr`, and `else_expr`
    of conditional assignments for literals.
    """
    model = {
        "global_variables": {
            "is_active": {"inferred_type": "boolean"},
            "result": {"inferred_type": "scalar"},
        },
        "user_defined_functions": {},
    }
    ir = {
        "pre_trial_steps": [
            # This conditional uses a variable for the condition, but literals for the branches.
            {"type": "conditional_assignment", "result": ["result"], "condition": "is_active", "then_expr": 100.0, "else_expr": [200.0, 300.0]}
        ]
    }

    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    assert result["constant_pools"]["SCALAR"] == [100.0]
    assert result["constant_pools"]["VECTOR"] == [[200.0, 300.0]]
    assert result["constant_map"]["s_100.0"]["index"] == 0


def test_finds_constants_in_deeply_nested_expressions():
    """
    Stress-tests the recursive literal finder with a complex, nested expression.
    """
    model = {"global_variables": {"x": {"inferred_type": "scalar"}}, "user_defined_functions": {}}
    ir = {
        "pre_trial_steps": [
            {
                "type": "execution_assignment",
                "result": ["x"],
                "function": "add",
                "args": [5.0, {"function": "multiply", "args": [10.0, [1.0, 2.0]]}],  # Top-level constant  # Nested constant  # Deeply nested constant vector
            }
        ]
    }
    allocator = ResourceAllocator(ir, model)
    result = allocator.allocate()

    # It should find all unique scalars and the unique vector.
    assert result["constant_pools"]["SCALAR"] == [5.0, 10.0]
    assert result["constant_pools"]["VECTOR"] == [[1.0, 2.0]]


def test_allocate_identity_scalar():
    model = {
        "global_variables": {"a": {"inferred_type": "scalar", "is_stochastic": False}},
    }
    ir = {"pre_trial_steps": [{"type": "copy", "result": ["a"], "source": 12, "line": 3}]}

    try:
        allocator = ResourceAllocator(ir, model)
        result = allocator.allocate()
        assert result["constant_pools"]["SCALAR"] == [12]
    except:
        pytest.fail("Failed to allocate scalar const from copy (identity) instruction")
