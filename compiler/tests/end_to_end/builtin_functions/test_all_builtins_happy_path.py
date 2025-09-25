import pytest
from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError
from .cases import BUILTIN_TEST_CASES
from tests.end_to_end.utils import _unpack_operand
from vsc.exceptions import ValuaScriptError

# --- Test Script Templates ---
HAPPY_PATH_TEMPLATE = """
@iterations=1
@output=x
{assignment} = {func_name}({args})
"""

# --- Test Case Generation ---
all_test_cases = []
for func_name, case_data in BUILTIN_TEST_CASES.items():
    # Create a copy and add the function name ('id') to the dictionary itself.
    case_with_id = case_data.copy()
    case_with_id["id"] = func_name
    # The `id=` here is just for the test report name. The `case_with_id` is what the test receives.
    all_test_cases.append(pytest.param(case_with_id, id=func_name))


@pytest.mark.parametrize("case", all_test_cases)
def test_happy_path_compilation(case):
    """
    Priority 1 Test: Verifies a standard, deterministic call for every
    built-in function is compiled with the correct structure and types.
    """
    script = HAPPY_PATH_TEMPLATE.format(assignment=case["happy_path"]["assignment"], func_name=case["id"], args=case["happy_path"]["args"])

    try:
        recipe = compile_valuascript(script)
    except ValuaScriptError as e:
        pytest.fail(f"A valid happy path for a builtin function failed with error: {e}")

    pre_trial_instructions = recipe["pre_trial_instructions"]
    per_trial_instructions = recipe["per_trial_instructions"]
    is_stochastic = case["happy_path"]["is_stochastic"]
    expected_opcode = case["happy_path"]["expected_opcode"]

    expected_srcs_count = case["happy_path"]["srcs_count"]
    expected_dests_count = case["happy_path"]["dests_count"]

    last_instruction = per_trial_instructions[-1] if is_stochastic else pre_trial_instructions[-1]

    srcs = last_instruction["srcs"]
    expected_srcs_types = case["happy_path"]["srcs_types"]
    dests = last_instruction["dests"]
    expected_dests_types = case["happy_path"]["dests_types"]

    variable_register_counts = case["happy_path"]["variable_register_counts"]
    constants = case["happy_path"].get("constants", None)

    assert len(per_trial_instructions if is_stochastic else pre_trial_instructions) == 1

    assert len(srcs) == expected_srcs_count
    assert len(dests) == expected_dests_count

    src_op_types = [_unpack_operand(op) for op in last_instruction["srcs"]]
    dest_op_types = [_unpack_operand(op) for op in last_instruction["dests"]]

    assert recipe["variable_register_counts"] == variable_register_counts

    assert src_op_types == expected_srcs_types
    assert dest_op_types == expected_dests_types

    will_be_folded = case["happy_path"].get("will_be_folded", False)

    if not will_be_folded:
        assert recipe["constants"] == constants

    assert last_instruction["op"] == (expected_opcode)
