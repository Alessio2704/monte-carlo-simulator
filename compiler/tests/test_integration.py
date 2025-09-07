import pytest
import sys
import os
import subprocess
import json
import tempfile

# Ensure the compiler's modules can be imported for direct use
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
            return path  # Return the first valid path found

    # If the executable was not found in any of the potential locations, skip the tests.
    pytest.skip(
        "Could not find C++ engine executable for integration tests. " "Ensure the engine has been built (e.g., `cmake --build build`).",
        allow_module_level=True,
    )


def run_preview_integration(script_content: str, preview_var: str, engine_path: str):
    """
    Performs a direct integration test by:
    1. Calling the compiler function to generate a recipe.
    2. Writing the recipe to a temporary file.
    3. Executing the C++ engine with the recipe.
    4. Parsing and returning the JSON output.
    """
    # Step 1: Compile the script in-process using the new compiler orchestrator
    recipe = compile_valuascript(script_content, preview_variable=preview_var)
    assert recipe is not None, "Compiler failed to produce a recipe"

    # Step 2: Write the generated recipe to a temporary file
    # We use delete=False because we need to pass the file path to another process
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_recipe_file:
        json.dump(recipe, tmp_recipe_file)
        recipe_path = tmp_recipe_file.name

    try:
        # Step 3: Execute the C++ engine directly with the recipe path
        result = subprocess.run([engine_path, "--preview", recipe_path], capture_output=True, text=True, check=True, timeout=10)  # This will raise an error on a non-zero exit code
        # Step 4: Parse and return the JSON from the engine's stdout
        return json.loads(result.stdout)
    finally:
        # Step 5: Clean up the temporary recipe file
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
    # Use pytest.approx for floating point comparisons
    if isinstance(expected_value, list):
        assert all(pytest.approx(a) == b for a, b in zip(result.get("value"), expected_value))
    else:
        assert pytest.approx(result.get("value")) == expected_value