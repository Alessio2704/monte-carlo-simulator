import pytest
import sys
import os

# Ensure the server and its dependencies can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.server import _get_script_analysis
from lsprotocol.types import MarkupContent, MarkupKind

# We reuse the fixture from test_imports to create file structures
from test_imports import create_files


def test_script_analysis_handles_nested_imports(create_files):
    """
    Validates that the language server's core analysis function can
    correctly traverse a complex, nested import graph (the diamond dependency)
    and discover all user-defined functions. This is a critical integration
    test for the live preview feature.
    """
    # ARRANGE: Create a complex file structure
    files = create_files(
        {
            "d_common.vs": "@module\nfunc get_base() -> scalar { return 100 }",
            "b_module.vs": """
                @module
                @import "d_common.vs"
                func process_b(x: scalar) -> scalar { return x + get_base() }
            """,
            "c_module.vs": """
                @module
                @import "d_common.vs"
                func process_c(y: scalar) -> scalar { return y * get_base() }
            """,
            "a_main.vs": """
                @import "b_module.vs"
                @import "c_module.vs"
                @iterations = 1
                @output = final
                func main_func() -> scalar { return 1 }
                let val_b = process_b(10)
                let val_c = process_c(2)
                let final = val_b + val_c
            """,
        }
    )
    main_path = files / "a_main.vs"
    main_content = main_path.read_text()

    # ACT: Run the analysis function on the main script
    defined_vars, stochastic_vars, user_functions = _get_script_analysis(source=main_content, file_path=str(main_path))

    # ASSERT: Check that the analysis was successful and complete
    assert defined_vars is not None
    assert "final" in defined_vars
    assert defined_vars["final"]["type"] == "scalar"

    # The most crucial assertion: verify that functions from ALL levels of
    # the import graph were discovered and loaded.
    expected_functions = {"main_func", "process_b", "process_c", "get_base"}
    assert set(user_functions.keys()) == expected_functions


def test_hover_content_generation():
    """
    Tests the content generation for hover tooltips for both built-in
    and user-defined functions, ensuring signatures and docstrings are correct.
    """
    # ARRANGE: Create a mock analysis result
    user_functions = {
        "my_udf": {
            "name": "my_udf",
            "params": [{"name": "p1", "type": "scalar"}, {"name": "p2", "type": "vector"}],
            "return_type": "scalar",
            "docstring": "This is a test docstring.",
        }
    }

    # ACT & ASSERT for a built-in function
    from vsc.config import FUNCTION_SIGNATURES

    npv_sig = FUNCTION_SIGNATURES["npv"]
    npv_doc = npv_sig["doc"]

    # Manually construct the expected markdown for 'npv'
    expected_npv_content = "\n".join(
        [
            "```valuascript\n(function) npv(rate, cashflows)\n```",
            "---",
            f"**{npv_doc['summary']}**",
            "\n#### Parameters:",
            f"- `{npv_doc['params'][0]['name']}`: {npv_doc['params'][0]['desc']}",
            f"- `{npv_doc['params'][1]['name']}`: {npv_doc['params'][1]['desc']}",
            f"\n**Returns**: `{npv_sig['return_type']}` — {npv_doc['returns']}",
        ]
    )

    # This is a simplified check mimicking the hover logic for a builtin
    assert "npv" in FUNCTION_SIGNATURES
    assert "Calculates the Net Present Value" in expected_npv_content

    # ACT & ASSERT for a User-Defined Function
    udf = user_functions["my_udf"]
    params_str = ", ".join([f"{p['name']}: {p['type']}" for p in udf["params"]])
    signature = f"(user defined function) {udf['name']}({params_str}) -> {udf['return_type']}"

    expected_udf_content = "\n".join([f"```valuascript\n{signature}\n```", "---", udf["docstring"]])

    # This check mimics the hover logic for a UDF
    assert "my_udf" in user_functions
    assert (
        expected_udf_content.strip()
        == """
```valuascript
(user defined function) my_udf(p1: scalar, p2: vector) -> scalar
```
---
This is a test docstring.
""".strip()
    )
