import os
from typing import Dict, Set

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import Root

from .module_loader import ModuleLoader


class ImportResolver:
    """
    Contains the pure logic for resolving an import graph.
    It uses a ModuleLoader to fetch ASTs and is responsible for:
    - Traversing the import graph.
    - Detecting circular dependencies.
    - Performing structural validation on imported modules.
    """

    def __init__(self, loader: ModuleLoader):
        self.loader = loader
        self.ast_map: Dict[str, Root] = {}
        self._import_stack: Set[str] = set()

    def resolve(self, main_ast: Root) -> Dict[str, Root]:
        """
        Takes the main entry-point AST and resolves all `@import` directives.
        Returns a map of absolute file paths to their corresponding ASTs.
        """
        self.ast_map = {main_ast.file_path: main_ast}
        self._import_stack = set()
        self._resolve_recursive(main_ast)
        return self.ast_map

    def _resolve_recursive(self, current_ast: Root):
        current_path = current_ast.file_path
        if current_path == "<stdin>":
            if current_ast.imports:
                raise ValuaScriptError(span=current_ast.imports[0].span, code=ErrorCode.CANNOT_IMPORT_FROM_STDIN)
            return

        self._import_stack.add(current_path)
        base_dir = os.path.dirname(current_path)

        for imp in current_ast.imports:
            abs_import_path = os.path.abspath(os.path.join(base_dir, imp.path))

            if abs_import_path in self._import_stack:
                raise ValuaScriptError(span=imp.span, code=ErrorCode.CIRCULAR_IMPORT, path=imp.path)

            if abs_import_path in self.ast_map:
                continue

            try:
                imported_ast = self.loader.load(abs_import_path)
                self._validate_module_structure(imported_ast, source_import_span=imp.span)
                self.ast_map[abs_import_path] = imported_ast
                self._resolve_recursive(imported_ast)
            except FileNotFoundError:
                raise ValuaScriptError(span=imp.span, code=ErrorCode.IMPORT_FILE_NOT_FOUND, path=imp.path)

        self._import_stack.remove(current_path)

    def _validate_module_structure(self, module_ast: Root, source_import_span):
        """Performs structural checks on a newly loaded module AST."""

        module_directive = [d for d in module_ast.directives if d.name == "module"]
        if module_directive:

            # Checks only one @module directive per file
            if len(module_directive) > 1:
                directive = module_directive[0]
                raise ValuaScriptError(span=directive.span, code=ErrorCode.MODULE_DIRECTIVE_DECLARED_MORE_THAN_ONCE)

            # Checks that module doesn't have a value associated
            if module_directive[0].value.value is not True and module_directive[0].value is not None:
                directive = module_directive[0]
                raise ValuaScriptError(span=directive.span, code=ErrorCode.MODULE_DIRECTIVE_WITH_VALUE)
        else:
            # Checks if no @module found
            raise ValuaScriptError(span=source_import_span, code=ErrorCode.IMPORT_NOT_A_MODULE, path=module_ast.file_path)

        # Checks that module doesn't have other directives
        other_directives = [d for d in module_ast.directives if d.name not in ["module"]]
        if other_directives:
            first_directive = other_directives[0]
            raise ValuaScriptError(span=first_directive.span, code=ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, name=first_directive.name)

        # Checks that module doesn't have global 'let' statements
        if module_ast.execution_steps:
            first_let = module_ast.execution_steps[0]
            raise ValuaScriptError(span=first_let.span, code=ErrorCode.GLOBAL_LET_IN_MODULE)
