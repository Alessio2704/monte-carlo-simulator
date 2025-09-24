import pytest
from pathlib import Path
from textwrap import dedent

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError

# --- Test Helpers ---


def create_dummy_file(directory: Path, filename: str, content: str) -> str:
    """Helper to create a temporary file for testing."""
    path = directory / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip())
    return str(path)


# --- Test Case ---


def test_vector_plus_vector_compiles_successfully(tmp_path):
    """
    This is a regression test for a bug where adding two vectors was
    incorrectly inferred as producing a scalar, causing a crash in the
    CodeEmitter.

    This test passes if the full compilation pipeline completes without error.
    """
    script = """
    @iterations = 1
    @output = result

    let v1 = [1, 2, 3]
    let v2 = [4, 5, 6]
    let v3 = [7, 8, 9]

    # This operation (vector + vector + vector) should result in a vector.
    let result = v1 + v2 + v3
    """
    main_file_path = create_dummy_file(tmp_path, "main.vs", script)

    try:
        # Run the full pipeline. This will raise an exception if the bug is present.
        recipe = compile_valuascript(script, file_path=main_file_path)

        # We can also add an assertion to be extra sure about the final recipe.
        assert "simulation_config" in recipe
        assert recipe["simulation_config"]["output_variable"] == "result"

    except Exception as e:
        pytest.fail(f"Full pipeline compilation failed for vector addition: {e}")
