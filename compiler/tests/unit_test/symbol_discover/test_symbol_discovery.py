import pytest
import os
from pathlib import Path

from vsc.parser.parser import parse_valuascript
from vsc.symbol_discovery import discover_symbols
from vsc.exceptions import ValuaScriptError, ErrorCode
from textwrap import dedent


# --- Helper to create dummy files for testing imports ---
def create_dummy_file(directory, filename, content):
    path = Path(directory) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return str(path)


# --- Tests for Basic Discovery and Metadata Extraction ---


def test_discover_simple_function_and_variable(tmp_path):
    """Tests basic discovery of a function and a global variable."""
    script_content = """
    # Main script
    let x = 10
    func my_func(a: scalar) -> scalar {
        let y = a + 5
        return y
    }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)

    # Check global variables
    assert "global_variables" in symbol_table
    assert "x" in symbol_table["global_variables"]
    assert symbol_table["global_variables"]["x"] == {
        "name": "x",
        "line": 3,
        "source_path": file_path,
    }

    # Check user-defined functions
    assert "user_defined_functions" in symbol_table
    assert "my_func" in symbol_table["user_defined_functions"]
    func_info = symbol_table["user_defined_functions"]["my_func"]
    assert func_info["name"] == "my_func"
    assert func_info["params"] == [{"name": "a", "type": "scalar"}]
    assert func_info["return_type"] == "scalar"
    assert func_info["docstring"] is None
    assert func_info["line"] == 4
    assert func_info["source_path"] == file_path
    assert func_info["ast_body"] == [
        {"type": "execution_assignment", "result": "y", "function": "add", "args": ["a", 5], "line": 5},
        {"type": "return_statement", "value": "y", "line": 6},
    ]  # Note: 'a' and 'y' are in AST, but only 'y' is discovered as local var

    # Check discovered body (local variables within the function)
    assert "discovered_body" in func_info
    assert "y" in func_info["discovered_body"]
    assert func_info["discovered_body"]["y"] == {
        "name": "y",
        "line": 5,
        "source_path": file_path,
    }
    assert "a" not in func_info["discovered_body"]  # Parameters are not considered 'discovered variables' here, they are separate metadata.


def test_discover_multiple_functions_and_variables(tmp_path):
    """Tests discovery with multiple functions and variables."""
    script_content = """
    let global_val_1 = 1.0
    let global_val_2 = "hello"

    func func1(p1: scalar) -> scalar {
        let local1 = p1 * 2
        return local1
    }

    func func2() -> scalar {
        let local2 = 100
        return local2
    }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)

    assert "global_val_1" in symbol_table["global_variables"]
    assert "global_val_2" in symbol_table["global_variables"]

    assert "func1" in symbol_table["user_defined_functions"]
    assert "func2" in symbol_table["user_defined_functions"]

    func1_info = symbol_table["user_defined_functions"]["func1"]
    print(func1_info)
    assert func1_info["discovered_body"]["local1"] == {"name": "local1", "line": 6, "source_path": file_path}

    func2_info = symbol_table["user_defined_functions"]["func2"]
    assert func2_info["discovered_body"]["local2"] == {"name": "local2", "line": 11, "source_path": file_path}


# --- Tests for Import Resolution ---


def test_discover_imports(tmp_path):
    """Tests discovery of functions and variables from imported modules."""
    module_content = """
    @module
    func module_func(x: scalar) -> scalar {
        return x + module_var
    }
    """
    main_content = """
    @import "module.vs"
    let main_var = module_func(module_var)
    """

    module_path = create_dummy_file(tmp_path, "module.vs", module_content)
    main_file_path = create_dummy_file(tmp_path, "main.vs", main_content)

    ast = parse_valuascript(main_content)
    symbol_table = discover_symbols(ast, main_file_path)

    # Check symbols from the main file
    assert "main_var" in symbol_table["global_variables"]
    assert symbol_table["global_variables"]["main_var"]["source_path"] == main_file_path

    # Check symbols from the imported module
    assert "module_func" in symbol_table["user_defined_functions"]
    assert symbol_table["user_defined_functions"]["module_func"]["source_path"] == module_path


def test_discover_multiple_imports(tmp_path):
    """Tests discovery with multiple imported modules."""
    module1_content = """
    @module
    func m1_func() -> scalar { return m1_val }
    """
    module2_content = """
    @module
    func m2_func() -> scalar { return m2_val }
    """
    main_content = """
    @import "module1.vs"
    @import "module2.vs"
    let result = m1_func() + m2_func()
    """

    create_dummy_file(tmp_path, "module1.vs", module1_content)
    create_dummy_file(tmp_path, "module2.vs", module2_content)
    main_file_path = create_dummy_file(tmp_path, "main.vs", main_content)

    ast = parse_valuascript(main_content)
    symbol_table = discover_symbols(ast, main_file_path)

    assert "m1_func" in symbol_table["user_defined_functions"]
    assert "m2_func" in symbol_table["user_defined_functions"]
    assert "result" in symbol_table["global_variables"]


def test_import_recursive_discovery(tmp_path):
    """Tests that importing a file that imports another works correctly."""
    module1_content = """
    @module
    func m1_func() -> scalar { return m1_global }
    """
    module2_content = """
    @module
    @import "module1.vs"
    func m2_func() -> scalar { return m1_func() + m2_global }
    """
    main_content = """
    @import "module2.vs"
    let main_result = m2_func()
    """

    create_dummy_file(tmp_path, "module1.vs", module1_content)
    create_dummy_file(tmp_path, "module2.vs", module2_content)
    main_file_path = create_dummy_file(tmp_path, "main.vs", main_content)

    ast = parse_valuascript(main_content)
    symbol_table = discover_symbols(ast, main_file_path)

    # Check that symbols from both modules are discoverable by the main file's discovery
    assert "m1_func" in symbol_table["user_defined_functions"]
    assert "m2_func" in symbol_table["user_defined_functions"]
    assert "main_result" in symbol_table["global_variables"]


# --- Tests for Name Uniqueness Enforcement ---


def test_duplicate_function_definition_same_file(tmp_path):
    """Tests that defining a function twice in the same file raises an error."""
    script_content = """
    func my_func() -> scalar { return 1 }
    func my_func() -> scalar { return 2 }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.DUPLICATE_FUNCTION


def test_duplicate_function_definition_imported(tmp_path):
    """Tests that defining a function twice across imported files raises an error."""
    module1_content = """
    @module
    func my_func() -> scalar { return 1 }
    """
    module2_content = """
    @module
    func my_func() -> scalar { return 2 }
    """
    main_content = """
    @import "module1.vs"
    @import "module2.vs"
    """

    module1_path = create_dummy_file(tmp_path, "module1.vs", module1_content)
    module2_path = create_dummy_file(tmp_path, "module2.vs", module2_content)
    main_file_path = create_dummy_file(tmp_path, "main.vs", main_content)

    ast = parse_valuascript(main_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, main_file_path)
    assert excinfo.value.code == ErrorCode.DUPLICATE_FUNCTION


def test_duplicate_global_variable_definition(tmp_path):
    """Tests that defining a global variable twice raises an error."""
    script_content = """
    let x = 10
    let x = 20
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.DUPLICATE_VARIABLE


def test_function_name_global_variable_collision(tmp_path):
    """Tests that a function and a global variable cannot have the same name."""
    script_content = """
    let my_var = 10
    func my_var() -> scalar { return 5 }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.DUPLICATE_VARIABLE


def test_global_variable_function_name_collision(tmp_path):
    """Tests that a global variable and a function cannot have the same name (reversed order)."""
    script_content = """
    func my_func() -> scalar { return 5 }
    let my_func = 10
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.DUPLICATE_VARIABLE


def test_function_name_builtin_collision(tmp_path):
    """Tests that a user-defined function cannot shadow a built-in function name."""
    script_content = """
    func Normal() -> scalar { return 1.0 } # Trying to redefine the Normal distribution
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.REDEFINE_BUILTIN_FUNCTION


# --- Tests for Import Error Handling ---


def test_import_file_not_found(tmp_path):
    """Tests that an error is raised if an imported file does not exist."""
    script_content = """
    @import "non_existent_module.vs"
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.IMPORT_FILE_NOT_FOUND
    assert "Imported file not found: 'non_existent_module.vs'" in str(excinfo.value)


# --- Tests for function body discovery ---


def test_discover_function_body_metadata(tmp_path):
    """Tests that ast_body and discovered_body are correctly populated."""
    script_content = """
    func complex_func(p1: scalar, p2: scalar) -> scalar {
        let intermediate_var = p1 * 2
        let final_var = intermediate_var + p2
        return final_var
    }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)

    assert "complex_func" in symbol_table["user_defined_functions"]
    func_info = symbol_table["user_defined_functions"]["complex_func"]

    # Check ast_body is the raw list of statements from the parser
    assert isinstance(func_info["ast_body"], list)
    assert len(func_info["ast_body"]) == 3  # 2 'let' statements + 1 'return' statement
    assert func_info["ast_body"][0]["type"] == "execution_assignment"
    assert func_info["ast_body"][0]["result"] == "intermediate_var"
    assert func_info["ast_body"][1]["type"] == "execution_assignment"
    assert func_info["ast_body"][1]["result"] == "final_var"
    assert func_info["ast_body"][2]["type"] == "return_statement"
    assert func_info["ast_body"][2]["value"] == "final_var"

    # Check discovered_body contains only the locally declared variables
    assert "discovered_body" in func_info
    assert len(func_info["discovered_body"]) == 2  # intermediate_var and final_var

    assert "intermediate_var" in func_info["discovered_body"]
    assert func_info["discovered_body"]["intermediate_var"] == {"name": "intermediate_var", "line": 3, "source_path": file_path}

    assert "final_var" in func_info["discovered_body"]
    assert func_info["discovered_body"]["final_var"] == {"name": "final_var", "line": 4, "source_path": file_path}

    # Ensure parameters are NOT in discovered_body
    assert "p1" not in func_info["discovered_body"]
    assert "p2" not in func_info["discovered_body"]


def test_discover_function_body_nested_variables(tmp_path):
    """Tests discovering variables within a function's body where an assignment is nested."""
    script_content = """
    func outer_func() -> scalar {
        let var1 = 1
        let var2 = var1 + 1
        let outer_var = var2 * 3 # This should discover outer_var
        return outer_var
    }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    func_info = symbol_table["user_defined_functions"]["outer_func"]

    assert "discovered_body" in func_info
    assert len(func_info["discovered_body"]) == 3  # var1, var2, outer_var

    assert "var1" in func_info["discovered_body"]
    assert "var2" in func_info["discovered_body"]
    assert "outer_var" in func_info["discovered_body"]


def test_discover_multi_variable_assignment_in_function(tmp_path):
    """Tests discovering multiple variables declared in a single multi-assignment statement within a function."""
    script_content = """
    func multi_assign_func() -> scalar {
        let a, b, c = get()
        return a + b + c
    }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)
    func_info = symbol_table["user_defined_functions"]["multi_assign_func"]

    assert "discovered_body" in func_info

    assert "a" in func_info["discovered_body"]
    assert "b" in func_info["discovered_body"]
    assert "c" in func_info["discovered_body"]
    assert func_info["discovered_body"]["a"]["line"] == 3
    assert func_info["discovered_body"]["b"]["line"] == 3
    assert func_info["discovered_body"]["b"]["line"] == 3


def test_discover_duplicate_variable_in_function(tmp_path):
    """Tests that redeclaring a variable within a function body raises an error."""
    script_content = """
    func func_with_dup() -> scalar {
        let x = 1
        let y = 2
        let x = 3 # Duplicate declaration
        return x + y
    }
    """
    file_path = os.path.join(str(tmp_path), "main.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.DUPLICATE_VARIABLE_IN_FUNC


# --- Tests for module specific directives ---
# Note: These are more for validating the 'module' flag behavior during discovery


def test_module_directive_prevents_global_vars(tmp_path):
    """Tests that global variables are not allowed in module files."""
    script_content = """
    @module
    let global_in_module = 10
    """
    file_path = os.path.join(str(tmp_path), "my_module.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.GLOBAL_LET_IN_MODULE


def test_module_directive_allows_functions(tmp_path):
    """Tests that functions ARE allowed in module files."""
    script_content = """
    @module
    func module_helper() -> scalar { return 1 }
    """
    file_path = os.path.join(str(tmp_path), "my_module.vs")
    with open(file_path, "w") as f:
        f.write(script_content)

    ast = parse_valuascript(script_content)
    try:
        symbol_table = discover_symbols(ast, file_path)
        assert "module_helper" in symbol_table["user_defined_functions"]
        assert symbol_table["user_defined_functions"]["module_helper"]["source_path"] == file_path
        assert "global_variables" in symbol_table
        assert len(symbol_table["global_variables"]) == 0  # No global variables allowed
    except ValuaScriptError as e:
        pytest.fail(f"Discovery failed unexpectedly: {e}")


def test_diamond_dependency_import(tmp_path):
    """
    Tests that a common file imported by multiple modules is processed only once.
    main -> module_a -> common
         -> module_b -> common
    """
    common_content = """
    @module
    func common_func() -> scalar { return 1 }
    """
    module_a_content = """
    @module
    @import "common.vs"
    func func_a() -> scalar { return common_func() }
    """
    module_b_content = """
    @module
    @import "common.vs"
    func func_b() -> scalar { return common_func() * 2 }
    """
    main_content = """
    @import "module_a.vs"
    @import "module_b.vs"
    let result = func_a() + func_b()
    """
    create_dummy_file(tmp_path, "common.vs", common_content)
    create_dummy_file(tmp_path, "module_a.vs", module_a_content)
    create_dummy_file(tmp_path, "module_b.vs", module_b_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)

    # The test is that this complex discovery runs without any errors.
    try:
        ast = parse_valuascript(main_content)
        symbol_table = discover_symbols(ast, main_path)
        # Assert that all functions were correctly discovered
        assert "common_func" in symbol_table["user_defined_functions"]
        assert "func_a" in symbol_table["user_defined_functions"]
        assert "func_b" in symbol_table["user_defined_functions"]
    except ValuaScriptError as e:
        pytest.fail(f"Diamond dependency test failed unexpectedly: {e}")


def test_parameter_local_variable_collision(tmp_path):
    """
    Tests that a local variable cannot be declared with the same name as a parameter.
    This is a critical scope validation check.
    """
    script_content = """
    func my_func(x: scalar) -> scalar {
        let y = 1
        let x = 2 # Illegal redeclaration of parameter 'x'
        return x + y
    }
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script_content)
    ast = parse_valuascript(script_content)

    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)

    assert excinfo.value.code == ErrorCode.DUPLICATE_VARIABLE_IN_FUNC


@pytest.mark.parametrize(
    "scope_setup, expected_error_code",
    [
        # Test in global scope
        ("let x, y, x = my_func()", ErrorCode.DUPLICATE_VARIABLE),
        # Test in local function scope
        (
            """
func my_func() -> scalar {
    let a, b, a = some_other_func()
    return a
}
         """,
            ErrorCode.DUPLICATE_VARIABLE_IN_FUNC,
        ),
    ],
    ids=["global_scope", "local_scope"],
)
def test_duplicate_variable_in_single_multi_assignment(tmp_path, scope_setup, expected_error_code):
    """
    Tests that declaring the same variable twice in a *single* multi-assignment
    statement is caught as an error.
    """
    # A dummy function definition is needed for the AST to be valid
    script_content = scope_setup + "\nfunc some_other_func() -> (scalar, scalar, scalar) { return (1,2,3) }"
    file_path = create_dummy_file(tmp_path, "main.vs", script_content)
    ast = parse_valuascript(script_content)

    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)

    assert excinfo.value.code == expected_error_code


@pytest.mark.parametrize("content", ["", "   \n\n  \t ", "# A file with only a comment"], ids=["empty_file", "whitespace_only", "comment_only"])
def test_empty_and_comment_only_files(tmp_path, content):
    """
    Tests that the discoverer handles empty or comment-only files gracefully,
    producing an empty symbol table.
    """
    file_path = create_dummy_file(tmp_path, "main.vs", content)
    ast = parse_valuascript(content)
    symbol_table = discover_symbols(ast, file_path)

    assert len(symbol_table["user_defined_functions"]) == 0
    assert len(symbol_table["global_variables"]) == 0
    assert file_path in symbol_table["processed_files"]


def test_function_with_no_local_variables(tmp_path):
    """
    Tests that a function with parameters but no local 'let' statements
    is discovered correctly with an empty 'discovered_body'.
    """
    script_content = """
    func no_locals(p1: scalar) -> scalar {
        return p1 * 2
    }
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script_content)
    ast = parse_valuascript(script_content)
    symbol_table = discover_symbols(ast, file_path)

    assert "no_locals" in symbol_table["user_defined_functions"]
    func_info = symbol_table["user_defined_functions"]["no_locals"]

    assert len(func_info["discovered_body"]) == 0
    assert len(func_info["ast_body"]) == 1  # Just the return statement
    assert func_info["ast_body"][0]["type"] == "return_statement"


def test_discover_imports_with_complex_paths(tmp_path):
    """
    Tests that the discoverer can resolve imports from subdirectories
    and parent directories.
    """
    # Create a directory structure:
    # tmp_path/
    #   project/
    #     main.vs
    #     modules/
    #       utils.vs
    #   common/
    #     helpers.vs

    helper_content = """
    @module
    func helper_func() -> scalar { return 100 }
    """
    utils_content = """
    @module
    @import "../../common/helpers.vs"
    func util_func() -> scalar { return helper_func() }
    """
    main_content = """
    @import "./modules/utils.vs"
    let x = util_func()
    """

    # Create the files in their respective directories
    project_dir = tmp_path / "project"
    modules_dir = project_dir / "modules"
    common_dir = tmp_path / "common"

    main_path = create_dummy_file(project_dir, "main.vs", main_content)
    utils_path = create_dummy_file(modules_dir, "utils.vs", utils_content)
    helper_path = create_dummy_file(common_dir, "helpers.vs", helper_content)

    ast = parse_valuascript(main_content)
    symbol_table = discover_symbols(ast, main_path)

    # Check that functions from all files were found via path resolution
    assert "helper_func" in symbol_table["user_defined_functions"]
    assert "util_func" in symbol_table["user_defined_functions"]
    assert "x" in symbol_table["global_variables"]

    # Check that the source paths are correctly stored as absolute paths
    assert symbol_table["user_defined_functions"]["helper_func"]["source_path"] == str(helper_path)
    assert symbol_table["user_defined_functions"]["util_func"]["source_path"] == str(utils_path)


def test_import_file_not_found(tmp_path):
    """Tests that an error is raised if an imported file does not exist."""
    script_content = """
    @import "non_existent_module.vs"
    """
    file_path = create_dummy_file(tmp_path, "main.vs", script_content)
    ast = parse_valuascript(script_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, file_path)
    assert excinfo.value.code == ErrorCode.IMPORT_FILE_NOT_FOUND
    assert "L2:" in str(excinfo.value)  # Check for line number


def test_circular_import(tmp_path):
    """Tests that circular imports are detected and reported."""

    # Using detent because multi line comment implicitly inserts a new line char

    module1_content = dedent(
        """
        @module
        @import "module2.vs"
    """
    ).strip()

    module2_content = dedent(
        """
        @module
        @import "module1.vs"
    """
    ).strip()

    module1_path = create_dummy_file(tmp_path, "module1.vs", module1_content)
    create_dummy_file(tmp_path, "module2.vs", module2_content)

    ast1 = parse_valuascript(module1_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast1, module1_path)
    assert excinfo.value.code == ErrorCode.CIRCULAR_IMPORT
    assert "L2:" in str(excinfo.value)


def test_importing_a_non_module_file_raises_error(tmp_path):
    """
    Tests that an error is raised if a file tries to import another file
    that is missing the @module directive.
    """
    non_module_content = """
    let x = 1 # This is a script, not a module
    """
    main_content = """
    @import "not_a_module.vs"
    """
    create_dummy_file(tmp_path, "not_a_module.vs", non_module_content)
    main_path = create_dummy_file(tmp_path, "main.vs", main_content)

    ast = parse_valuascript(main_content)
    with pytest.raises(ValuaScriptError) as excinfo:
        discover_symbols(ast, main_path)

    assert excinfo.value.code == ErrorCode.IMPORT_NOT_A_MODULE
    assert "Imported file 'not_a_module.vs' is not a valid module" in str(excinfo.value)
    assert "L2:" in str(excinfo.value)  # Check that the error is reported on the @import line
