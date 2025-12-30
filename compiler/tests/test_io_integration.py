import pytest
import sys
import os
import subprocess
import json
import tempfile


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vsc.compiler import compile_valuascript


from test_integration import find_engine_path, run_preview_integration


@pytest.fixture
def create_test_csv(tmp_path):
    """Creates a sample CSV file for testing read operations."""
    csv_content = "Year,Revenue,Cost\n2023,1000,600\n2024,1200,700\n2025,1400,800"
    csv_path = tmp_path / "test_data.csv"
    csv_path.write_text(csv_content)
    return csv_path


def test_read_csv_scalar_integration(find_engine_path, create_test_csv):
    """
    Tests that the compiler and engine can correctly read a single value
    from an external CSV file.
    """
    test_csv_path = create_test_csv
    script = f"""
    @iterations=1
    @output=revenue_2024
    let revenue_2024 = read_csv_scalar("{test_csv_path}", "Revenue", 1) # Row 1 (2024), "Revenue" column
    """
    result = run_preview_integration(script, "revenue_2024", find_engine_path)
    assert result.get("status") == "success"
    assert result.get("type") == "scalar"
    assert pytest.approx(result.get("value")) == 1200.0


def test_read_csv_vector_integration(find_engine_path, create_test_csv):
    """
    Tests that the compiler and engine can correctly read an entire column
    from an external CSV file into a vector.
    """
    test_csv_path = create_test_csv
    script = f"""
    @iterations=1
    @output=all_costs
    let all_costs = read_csv_vector("{test_csv_path}", "Cost")
    """
    result = run_preview_integration(script, "all_costs", find_engine_path)
    assert result.get("status") == "success"
    assert result.get("type") == "vector"
    assert result.get("value") == [600.0, 700.0, 800.0]
