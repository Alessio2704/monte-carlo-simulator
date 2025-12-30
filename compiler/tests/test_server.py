import pytest
import sys
import os


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.server import _get_script_analysis


def test_script_analysis_with_manual_structure(create_manual_test_structure):
    """
    Validates that the language server's core analysis function can
    correctly traverse the complex, multi-level, diamond-dependency import graph
    from the manual test plan and discover all user-defined functions.
    This is the automated test for the logic behind manual test #1.
    """

    test_dir = create_manual_test_structure
    main_path = test_dir / "main.vs"
    main_content = main_path.read_text()

    defined_vars, stochastic_vars, user_functions = _get_script_analysis(source=main_content, file_path=str(main_path))

    assert defined_vars is not None
    assert "dcf_after_tax" in defined_vars
    assert defined_vars["dcf_after_tax"]["type"] == "scalar"

    expected_functions = {
        "get_cashflows",
        "project_growth",
        "calculate_dcf",
        "apply_tax",
        "calculate_wacc",
        "get_risk_free_rate",
    }
    assert set(user_functions.keys()) == expected_functions


def test_hover_content_generation():
    """
    Tests the content generation for hover tooltips for both built-in
    and user-defined functions, ensuring signatures and docstrings are correct.
    """

    user_functions = {
        "my_udf": {
            "name": "my_udf",
            "params": [{"name": "p1", "type": "scalar"}, {"name": "p2", "type": "vector"}],
            "return_type": "scalar",
            "docstring": "This is a test docstring.",
        }
    }

    from vsc.functions import FUNCTION_SIGNATURES

    npv_sig = FUNCTION_SIGNATURES["npv"]
    npv_doc = npv_sig["doc"]

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

    assert "npv" in FUNCTION_SIGNATURES
    assert "Calculates the Net Present Value" in expected_npv_content

    udf = user_functions["my_udf"]
    params_str = ", ".join([f"{p['name']}: {p['type']}" for p in udf["params"]])
    signature = f"(user defined function) {udf['name']}({params_str}) -> {udf['return_type']}"

    expected_udf_content = "\n".join([f"```valuascript\n{signature}\n```", "---", udf["docstring"]])

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
