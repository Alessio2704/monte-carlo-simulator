import subprocess
import sys
import os
import pytest


def test_cli_successful_compilation_and_run(create_manual_test_structure):
    """
    Tests that `vsc main.vs --run` executes successfully on a complex,
    multi-file project.
    """
    test_dir = create_manual_test_structure
    main_script_path = test_dir / "main.vs"

    command = [sys.executable, "-m", "vsc", str(main_script_path), "--run"]

    result = subprocess.run(command, capture_output=True, text=True, cwd=test_dir)

    assert result.returncode == 0, f"CLI should have succeeded but failed with stderr:\n{result.stderr}"
    assert "Compilation Successful" in result.stdout
    assert "Simulation Finished Successfully" in result.stdout
    assert os.path.exists(test_dir / "simulation_output.csv")


def test_cli_circular_import_error(create_manual_test_structure):
    """
    Tests that the CLI correctly fails and reports a circular import error
    when compiling a file that is part of an import cycle.
    """
    test_dir = create_manual_test_structure
    cycle_script_path = test_dir / "cycle" / "cycle_a.vs"

    command = [sys.executable, "-m", "vsc", str(cycle_script_path)]

    result = subprocess.run(command, capture_output=True, text=True, cwd=test_dir)

    assert result.returncode != 0, "CLI should have failed but it succeeded."
    assert "COMPILATION ERROR" in result.stderr
    assert "Circular import detected" in result.stderr
