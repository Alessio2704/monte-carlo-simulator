import pytest
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any

# --- Full Compiler Pipeline ---
from vsc.compiler import compile_valuascript

# --- Test Helpers ---


def create_dummy_file(directory: Path, filename: str, content: str) -> str:
    """Helper to create files for tests."""
    path = directory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip())
    return str(path)


# --- Test Case ---


def test_bytecode_generation_for_a_mixed_script(tmp_path):
    """
    This is a full end-to-end integration test that verifies the final
    JSON recipe is generated correctly from a script with both deterministic
    and stochastic components.
    """

    script = dedent(
        """
    @iterations = 50000
    @output = z
    
    # This variable is deterministic but cannot be folded into a constant literal.
    let d_vec = grow_series(100, 0, 1)
    let d_val = d_vec[0]
    
    # This variable and its dependency must be calculated in each trial.
    let s_val = Normal(0, 1)
    let z = d_val + s_val
    """
    ).strip()
    main_path = create_dummy_file(tmp_path, "main.vs", script)

    recipe = compile_valuascript(script, file_path=main_path)

    # --- 1. Assert Simulation Config ---
    assert "simulation_config" in recipe
    assert recipe["simulation_config"] == {"num_trials": 50000}

    # --- 2. Assert Variable Registry ---
    # Now, d_val and d_vec MUST be in the final registry.
    assert "variable_registry" in recipe
    expected_registry = ["d_val", "d_vec", "s_val", "z"]  # Sorted alphabetically
    assert recipe["variable_registry"] == expected_registry

    # --- 3. Assert Output Variable Index ---
    assert "output_variable_index" in recipe
    assert recipe["output_variable_index"] == expected_registry.index("z")

    # --- 4. Assert Pre-Trial (Deterministic) Steps ---
    assert "pre_trial_steps" in recipe
    pre_trial = recipe["pre_trial_steps"]

    # There should now be two pre-trial steps: one for 'd_vec' and one for 'd_val'
    assert len(pre_trial) == 2

    # -- Verify the 'd_vec' step --
    d_vec_step = next(s for s in pre_trial if s["result"] == [expected_registry.index("d_vec")])
    assert d_vec_step is not None
    assert d_vec_step["type"] == "execution_assignment"
    assert d_vec_step["function"] == "grow_series"
    assert d_vec_step["line"] == 5

    # -- Verify the 'd_val' step --
    d_val_step = next(s for s in pre_trial if s["result"] == [expected_registry.index("d_val")])
    assert d_val_step is not None
    assert d_val_step["type"] == "execution_assignment"
    assert d_val_step["function"] == "get_element"
    assert d_val_step["line"] == 6
    assert d_val_step["args"][0]["value"] == expected_registry.index("d_vec")

    # --- 5. Assert Per-Trial (Stochastic) Steps ---
    assert "per_trial_steps" in recipe
    per_trial = recipe["per_trial_steps"]

    assert len(per_trial) == 2

    # -- Verify the 's_val' step --
    s_val_step = next(s for s in per_trial if s["result"] == [expected_registry.index("s_val")])
    assert s_val_step is not None
    assert s_val_step["function"] == "Normal"
    assert s_val_step["line"] == 9

    # -- Verify the 'z' step --
    z_step = next(s for s in per_trial if s["result"] == [expected_registry.index("z")])
    assert z_step is not None
    assert z_step["function"] == "add"
    assert z_step["line"] == 10
    z_args = z_step["args"]
    assert z_args[0]["value"] == expected_registry.index("d_val")
    assert z_args[1]["value"] == expected_registry.index("s_val")
