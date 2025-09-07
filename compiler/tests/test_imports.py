import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from vsc.compiler import compile_valuascript
from vsc.exceptions import ValuaScriptError, ErrorCode

# --- Fixture to set up file structures ---


@pytest.fixture
def create_files(tmp_path):
    """A factory fixture to create a temporary file structure for import tests."""

    def _create_files(file_dict):
        for file_path, content in file_dict.items():
            path = tmp_path / file_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return tmp_path

    return _create_files


# --- 1. VALID IMPORT SCENARIOS ---


def test_simple_valid_import(create_files):
    """Tests a basic import from a runnable script to a single module."""
    files = create_files(
        {
            "utils.vs": """
                @module
                func add_one(x: scalar) -> scalar { return x + 1 }
            """,
            "main.vs": """
                @import "utils.vs"
                @iterations = 1
                @output = result
                let result = add_one(10)
            """,
        }
    )
    main_path = files / "main.vs"
    recipe = compile_valuascript(main_path.read_text(), file_path=str(main_path))
    assert recipe is not None
    assert "__add_one_1__x" in recipe["variable_registry"]


def test_import_from_subdirectory(create_files):
    """Tests that the compiler can resolve paths into subdirectories."""
    files = create_files(
        {
            "modules/math.vs": """
                @module
                func multiply_by_two(a: scalar) -> scalar { return a * 2 }
            """,
            "main.vs": """
                @import "modules/math.vs"
                @iterations = 1
                @output = result
                let result = multiply_by_two(5)
            """,
        }
    )
    main_path = files / "main.vs"
    recipe = compile_valuascript(main_path.read_text(), file_path=str(main_path))
    assert recipe is not None
    assert "__multiply_by_two_1__a" in recipe["variable_registry"]


def test_multiple_imports(create_files):
    """Tests a script importing functions from two different modules."""
    files = create_files(
        {
            "adder.vs": "@module\nfunc add_nums(a: scalar, b: scalar) -> scalar { return a + b }",
            "subtracter.vs": "@module\nfunc sub_nums(a: scalar, b: scalar) -> scalar { return a - b }",
            "main.vs": """
                @import "adder.vs"
                @import "subtracter.vs"
                @iterations = 1
                @output = y
                let x = add_nums(1, 2)
                let y = sub_nums(x, 1)
            """,
        }
    )
    main_path = files / "main.vs"
    recipe = compile_valuascript(main_path.read_text(), file_path=str(main_path))
    assert recipe is not None
    assert any(v.startswith("__add_nums_") for v in recipe["variable_registry"])
    assert any(v.startswith("__sub_nums_") for v in recipe["variable_registry"])


def test_nested_import(create_files):
    """Tests that a module can import from another module (A -> B -> C)."""
    files = create_files(
        {
            # FIX: Add a local variable to force the inliner to create a mangled variable.
            "c.vs": """
                @module
                func get_number() -> scalar {
                    let the_answer = 42
                    return the_answer
                }
            """,
            "b.vs": """
                @module
                @import "c.vs"
                func add_ten(x: scalar) -> scalar {
                    let base = get_number()
                    return x + 10 + base
                }
            """,
            "a.vs": """
                @import "b.vs"
                @iterations = 1
                @output = result
                let result = add_ten(5)
            """,
        }
    )
    main_path = files / "a.vs"
    recipe = compile_valuascript(main_path.read_text(), file_path=str(main_path))
    assert recipe is not None
    assert "result" in recipe["variable_registry"]
    assert any(v.startswith("__add_ten_") for v in recipe["variable_registry"])
    # This assertion will now pass because "__get_number_1__the_answer" will exist.
    assert any(v.startswith("__get_number_") for v in recipe["variable_registry"])


# --- 2. INVALID IMPORT SCENARIOS (ERROR HANDLING) ---


@pytest.mark.parametrize(
    "files, main_script, expected_error_code",
    [
        pytest.param({}, '@import "non_existent.vs"', ErrorCode.IMPORT_FILE_NOT_FOUND, id="file_not_found"),
        pytest.param({"not_a_module.vs": "let x = 1"}, '@import "not_a_module.vs"', ErrorCode.IMPORT_NOT_A_MODULE, id="import_not_a_module"),
        pytest.param({"invalid_module.vs": "@module\nlet y = 1"}, '@import "invalid_module.vs"', ErrorCode.GLOBAL_LET_IN_MODULE, id="import_invalid_module"),
        pytest.param(
            {
                "a.vs": '@module\n@import "b.vs"',
                "b.vs": '@module\n@import "a.vs"',
            },
            '@import "a.vs"',
            ErrorCode.CIRCULAR_IMPORT,
            id="circular_import_disallowed",
        ),
        pytest.param(
            {
                "module1.vs": "@module\nfunc conflict() -> scalar { return 1 }",
                "module2.vs": "@module\nfunc conflict() -> scalar { return 2 }",
            },
            '@import "module1.vs"\n@import "module2.vs"',
            ErrorCode.FUNCTION_NAME_COLLISION,
            id="collision_between_modules",
        ),
        pytest.param(
            {"utils.vs": "@module\nfunc my_func() -> scalar { return 1 }"},
            '@import "utils.vs"\nfunc my_func() -> scalar { return 2 }',
            ErrorCode.FUNCTION_NAME_COLLISION,
            id="collision_main_and_module",
        ),
    ],
)
def test_import_errors(create_files, files, main_script, expected_error_code):
    """A comprehensive test for various import-related compiler errors."""
    file_structure = create_files(files)
    main_content = f"""
    @iterations=1
    @output=x
    let x = 1
    {main_script}
    """
    main_path = file_structure / "main.vs"
    main_path.write_text(main_content)

    with pytest.raises(ValuaScriptError) as e:
        compile_valuascript(main_path.read_text(), file_path=str(main_path))
    assert e.value.code == expected_error_code


def test_import_from_stdin_fails():
    """Ensures the compiler correctly forbids imports when compiling from stdin."""
    script = '@import "some_module.vs"\n@iterations=1\n@output=x\nlet x=1'
    with pytest.raises(ValuaScriptError) as e:
        # file_path is not provided, simulating stdin
        compile_valuascript(script)
    assert e.value.code == ErrorCode.CANNOT_IMPORT_FROM_STDIN
