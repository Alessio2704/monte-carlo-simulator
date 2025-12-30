import pytest
import sys
import os
import subprocess
import json
import tempfile
import pandas as pd


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError


@pytest.fixture
def find_engine_path():
    """
    A helper to find the C++ engine for integration tests.
    This is platform-aware and checks for configuration-specific build
    directories (like 'Release') on Windows.
    """
    engine_name = "vse.exe" if sys.platform == "win32" else "vse"
    base_build_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "build", "bin"))

    potential_paths = []
    if sys.platform == "win32":
        # On Windows, MSBuild creates configuration-specific subdirectories.
        # The CI pipeline builds in 'Release' mode. We also check for 'Debug'
        # to support local development.
        potential_paths.append(os.path.join(base_build_path, "Release", engine_name))
        potential_paths.append(os.path.join(base_build_path, "Debug", engine_name))

    # For non-Windows platforms or as a fallback, check the base bin directory.
    potential_paths.append(os.path.join(base_build_path, engine_name))

    for path in potential_paths:
        if os.path.exists(path):
            return path

    # If the executable was not found in any of the potential locations, skip the tests.
    pytest.skip(
        "Could not find C++ engine executable for integration tests. " "Ensure the engine has been built (e.g., `cmake --build build`).",
        allow_module_level=True,
    )


def run_preview_integration(script_content: str, preview_var: str, engine_path: str, file_path: str = None):
    """
    Performs a direct integration test by:
    1. Calling the compiler function to generate a recipe.
    2. Writing the recipe to a temporary file.
    3. Executing the C++ engine with the recipe.
    4. Parsing and returning the JSON output.
    """

    recipe = compile_valuascript(script_content, preview_variable=preview_var, file_path=file_path)
    assert recipe is not None, "Compiler failed to produce a recipe"

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_recipe_file:
        json.dump(recipe, tmp_recipe_file)
        recipe_path = tmp_recipe_file.name

    try:

        result = subprocess.run([engine_path, "--preview", recipe_path], capture_output=True, text=True, check=True, timeout=10)

        return json.loads(result.stdout)
    finally:

        os.remove(recipe_path)


@pytest.mark.parametrize(
    "script, preview_var, expected_type, expected_value",
    [
        pytest.param("@output=b\n@iterations=1\nlet a=100\nlet b=a*2", "b", "scalar", 200.0, id="deterministic_scalar"),
        pytest.param("@output=x\n@iterations=100\nlet x=Normal(100,0)", "x", "scalar", 100.0, id="stochastic_scalar"),
        pytest.param(
            """
            @output=v
            @iterations=1
            func my_vec() -> vector { return [10, 20, 30] }
            let v = my_vec()
            """,
            "v",
            "vector",
            [10.0, 20.0, 30.0],
            id="udf_returning_vector",
        ),
        pytest.param(
            """
            @output=z
            @iterations=1
            func my_add(a: scalar, b: scalar) -> scalar { return a + b }
            let x = 10
            let y = 20
            let z = my_add(x, y)
            """,
            "z",
            "scalar",
            30.0,
            id="udf_with_params",
        ),
    ],
)
def test_preview_integration(find_engine_path, script, preview_var, expected_type, expected_value):
    """
    A comprehensive suite of end-to-end tests for the preview feature,
    covering various language constructs from simple literals to UDFs.
    """
    result = run_preview_integration(script, preview_var, find_engine_path)

    assert result.get("status") == "success"
    assert result.get("type") == expected_type

    if isinstance(expected_value, list):
        assert all(pytest.approx(a) == b for a, b in zip(result.get("value"), expected_value))
    else:
        assert pytest.approx(result.get("value")) == expected_value


def test_preview_integration_with_deeply_nested_imports(create_manual_test_structure, find_engine_path):
    """
    Automates the most critical manual test: previewing a variable that
    depends on a complex, multi-level, diamond-shaped import graph.
    This validates that the compiler and engine work together seamlessly
    to resolve and compute values across the entire project structure.
    """

    test_dir = create_manual_test_structure
    main_script_path = test_dir / "main.vs"
    script_content = main_script_path.read_text()

    result = run_preview_integration(script_content=script_content, preview_var="dcf_value", engine_path=find_engine_path, file_path=str(main_script_path))

    assert result.get("status") == "success"
    assert result.get("type") == "scalar"

    assert pytest.approx(result.get("value"), abs=1e-2) == 186.90


def test_full_run_and_csv_output_validation(find_engine_path, tmp_path):
    """
    Performs a full end-to-end test of the `--run` command and validates
    the content of the final CSV output. This confirms the entire toolchain,
    from compilation to engine execution to file output, is working correctly
    for a deterministic calculation.
    """

    script = """
    @iterations = 1
    @output = c
    @output_file = "deterministic_out.csv"
    let a = 10
    let b = 20
    let c = a + b # The result should always be 30
    """
    script_path = tmp_path / "main.vs"
    script_path.write_text(script)

    recipe_path = tmp_path / "main.json"
    output_csv_path = tmp_path / "deterministic_out.csv"

    compile_command = [sys.executable, "-m", "vsc", str(script_path), "-o", str(recipe_path)]
    subprocess.run(compile_command, check=True)
    assert os.path.exists(recipe_path)

    engine_path = find_engine_path
    engine_command = [engine_path, str(recipe_path)]
    subprocess.run(engine_command, check=True, cwd=tmp_path)
    assert os.path.exists(output_csv_path)

    df = pd.read_csv(output_csv_path)
    assert "Result" in df.columns
    assert len(df) == 1
    assert pytest.approx(df["Result"].iloc[0]) == 30.0
