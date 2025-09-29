import pytest

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import Root
from vsc.parser.utils.factory_helpers import get_directive, get_literal_assignment, get_number_literal
from vsc.semantic_analyser.core.import_resolver import ImportResolver
from vsc.semantic_analyser.utils.factory_helpers import get_root_with_import


class MockModuleLoader:
    """A fake loader that serves pre-defined ASTs from a dictionary."""

    def __init__(self, available_asts: dict[str, Root]):
        self.available_asts = available_asts

    def load(self, absolute_path: str) -> Root:
        if absolute_path in self.available_asts:
            return self.available_asts[absolute_path]
        raise FileNotFoundError()


def test_import_not_module_raises_error():
    # --- ARRANGE ---
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs"])
    module_a_ast = get_root_with_import(main_file_path="/project/module_a.vs", imports=[], is_module=False)

    mock_loader = MockModuleLoader({"/project/main.vs": main_ast, "/project/module_a.vs": module_a_ast})

    # Instantiate the resolver with our mock loader
    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    with pytest.raises(ValuaScriptError) as exc_info:
        resolver.resolve(main_ast)

    assert exc_info.value.code == ErrorCode.IMPORT_NOT_A_MODULE


def test_circular_import_raises_error():
    # --- ARRANGE ---
    # Define our virtual files as pure AST objects
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs"])
    module_a_ast = get_root_with_import(main_file_path="/project/module_a.vs", imports=["/project/main.vs"], is_module=True)

    # Create a mock loader that knows about these ASTs
    mock_loader = MockModuleLoader(
        {
            "/project/main.vs": main_ast,
            "/project/module_a.vs": module_a_ast,
        }
    )

    # Instantiate the resolver with our mock loader
    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    with pytest.raises(ValuaScriptError) as exc_info:
        resolver.resolve(main_ast)

    assert exc_info.value.code == ErrorCode.CIRCULAR_IMPORT


def test_module_with_let_statement_raises_error():

    # --- ARRANGE ---
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs"])
    # This module is invalid because it has a 'let' statement
    invalid_module_ast = get_root_with_import(main_file_path="/project/module_a.vs", imports=[], is_module=True)

    invalid_module_ast.execution_steps.append(get_literal_assignment(target="a", value=get_number_literal(1)))

    mock_loader = MockModuleLoader({"/project/module_a.vs": invalid_module_ast})
    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    with pytest.raises(ValuaScriptError) as exc_info:
        resolver.resolve(main_ast)

    assert exc_info.value.code == ErrorCode.GLOBAL_LET_IN_MODULE


def test_module_with_other_directives_raises_error():

    # --- ARRANGE ---
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs"])
    # This module is invalid because it has a 'let' statement
    invalid_module_ast = get_root_with_import(main_file_path="/project/module_a.vs", imports=[], is_module=True)

    invalid_module_ast.directives.append(get_directive(name="iterations", value=get_number_literal(value=1000)))

    mock_loader = MockModuleLoader({"/project/module_a.vs": invalid_module_ast})
    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    with pytest.raises(ValuaScriptError) as exc_info:
        resolver.resolve(main_ast)

    assert exc_info.value.code == ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE


def test_module_not_found_raises_error():

    # --- ARRANGE ---
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs"])

    mock_loader = MockModuleLoader({})
    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    with pytest.raises(ValuaScriptError) as exc_info:
        resolver.resolve(main_ast)

    assert exc_info.value.code == ErrorCode.IMPORT_FILE_NOT_FOUND


def test_module_with_value_raises_error():

    # --- ARRANGE ---
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs"])
    invalid_module_ast = get_root_with_import(main_file_path="/project/module_a.vs", imports=[], is_module=True)

    invalid_module_ast.directives[0].value.value = 1000

    mock_loader = MockModuleLoader({"/project/module_a.vs": invalid_module_ast})
    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    with pytest.raises(ValuaScriptError) as exc_info:
        resolver.resolve(main_ast)

    assert exc_info.value.code == ErrorCode.MODULE_DIRECTIVE_WITH_VALUE


def test_module_directive_more_than_once_raises_error():

    # --- ARRANGE ---
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs"])
    invalid_module_ast = get_root_with_import(main_file_path="/project/module_a.vs", imports=[], is_module=True)

    invalid_module_ast.directives.append(get_directive("module", True))

    mock_loader = MockModuleLoader({"/project/module_a.vs": invalid_module_ast})
    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    with pytest.raises(ValuaScriptError) as exc_info:
        resolver.resolve(main_ast)

    assert exc_info.value.code == ErrorCode.MODULE_DIRECTIVE_DECLARED_MORE_THAN_ONCE


def test_resolve_with_no_imports():
    # ARRANGE
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=[])
    mock_loader = MockModuleLoader({})  # The loader will never be called
    resolver = ImportResolver(loader=mock_loader)

    # ACT
    ast_map = resolver.resolve(main_ast)

    # ASSERT
    assert len(ast_map) == 1
    assert main_ast.file_path in ast_map


def test_resolve_with_stdin_and_no_imports_is_ok():
    # ARRANGE
    main_ast = get_root_with_import(main_file_path="<stdin>", imports=[])
    resolver = ImportResolver(loader=MockModuleLoader({}))

    # ACT
    ast_map = resolver.resolve(main_ast)

    # ASSERT
    assert len(ast_map) == 1
    assert "<stdin>" in ast_map


def test_diamond_import_is_ok():
    # --- ARRANGE ---
    main_ast = get_root_with_import(main_file_path="/project/main.vs", imports=["/project/module_a.vs", "/project/module_b.vs"])
    module_a_ast = get_root_with_import(main_file_path="/project/module_a.vs", imports=["/project/shared.vs"], is_module=True)
    module_b_ast = get_root_with_import(main_file_path="/project/module_b.vs", imports=["/project/shared.vs"], is_module=True)
    module_shared_ast = get_root_with_import(main_file_path="/project/shared.vs", imports=[], is_module=True)

    mock_loader = MockModuleLoader(
        {
            "/project/main.vs": main_ast,
            "/project/module_a.vs": module_a_ast,
            "/project/module_b.vs": module_b_ast,
            "/project/shared.vs": module_shared_ast,
        }
    )

    resolver = ImportResolver(loader=mock_loader)

    # --- ACT & ASSERT ---
    result = resolver.resolve(main_ast)

    assert "/project/main.vs" in result
    assert "/project/module_a.vs" in result
    assert "/project/module_b.vs" in result
    assert "/project/shared.vs" in result

    assert len(result) == 4
