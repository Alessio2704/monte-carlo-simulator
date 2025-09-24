# import pytest


# def test_all_builtins_are_covered_by_end_to_end_tests():
#     """
#     This is a meta-test to ensure our test suite is complete.

#     It checks that every user-callable built-in function defined in the compiler
#     has a corresponding entry in the `builtin_test_cases` registry.
#     It also checks for the reverse, ensuring no obsolete test cases exist.
#     """
#     # 1. ARRANGE: Discover all functions from the compiler's source of truth.
#     from vsc.functions import FUNCTION_SIGNATURES

#     # Filter out internal operators (like __add__, __eq__) which are not
#     # tested via this specific end-to-end framework.
#     public_builtins = {name for name in FUNCTION_SIGNATURES.keys() if not name.startswith("__")}

#     # 2. ARRANGE: Load all function names from our test case registry.
#     from tests.end_to_end.builtin.builtin_test_cases import BUILTIN_TEST_CASES

#     tested_functions = set(BUILTIN_TEST_CASES.keys())

#     # 3. ACT & ASSERT: Find any functions that are implemented but not tested.
#     untested_functions = public_builtins - tested_functions

#     if untested_functions:
#         # Provide a clear, actionable error message.
#         error_message = (
#             f"The following {len(untested_functions)} built-in functions are defined in "
#             f"`vsc/functions/` but are missing a test case in "
#             f"`tests/end_to_end/builtin_test_cases.py`:\n"
#             f"{sorted(list(untested_functions))}"
#         )
#         pytest.fail(error_message)

#     # 4. ACT & ASSERT: Find any test cases for functions that no longer exist.
#     obsolete_test_cases = tested_functions - public_builtins

#     if obsolete_test_cases:
#         error_message = (
#             f"The following {len(obsolete_test_cases)} test cases exist in "
#             f"`tests/end_to_end/builtin_test_cases.py` but the corresponding "
#             f"functions are not defined in `vsc/functions/`:\n"
#             f"{sorted(list(obsolete_test_cases))}"
#         )
#         pytest.fail(error_message)
