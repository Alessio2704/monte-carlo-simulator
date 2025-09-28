import os
from typing import Dict, Set

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import Root
from vsc.parser.core.parser import parse_valuascript


def _resolve_recursive(current_ast: Root, ast_map: Dict[str, Root], import_stack: Set[str]):
    """Recursively resolves imports for a given AST."""
    current_path = current_ast.file_path
    if current_path == "<stdin>":
        # If there are imports while in stdin mode, we must fail.
        if current_ast.imports:
            first_import_span = current_ast.imports[0].span
            raise ValuaScriptError(code=ErrorCode.CANNOT_IMPORT_FROM_STDIN, span=first_import_span)
        return

    # Add the current path to the stack for cycle detection.
    import_stack.add(current_path)
    base_dir = os.path.dirname(current_path)

    for imp in current_ast.imports:
        # Resolve the imported file path relative to the current file.
        import_path = os.path.join(base_dir, imp.path)
        abs_import_path = os.path.abspath(import_path)

        # --- Circular Import Check ---
        if abs_import_path in import_stack:
            raise ValuaScriptError(code=ErrorCode.CIRCULAR_IMPORT, span=imp.span, path=imp.path)

        # If we have already parsed this file, skip it.
        if abs_import_path in ast_map:
            continue

        # --- Read and Parse the Imported File ---
        try:
            with open(abs_import_path, "r", encoding="utf-8") as f:
                content = f.read()

            imported_ast = parse_valuascript(content, file_path=abs_import_path)

            # Check if the imported file is a module
            is_module = any(d.name == "module" for d in imported_ast.directives)
            if not is_module:
                raise ValuaScriptError(code=ErrorCode.IMPORT_NOT_A_MODULE, span=imp.span, path=imp.path)

            if len(imported_ast.directives) > 1:
                first_directive = imported_ast.directives[1]
                found_directive_name = f"@{first_directive.name}"

                if first_directive:
                    raise ValuaScriptError(
                        code=ErrorCode.INVALID_DIRECTIVE_IN_MODULE,
                        span=first_directive.span,
                        found_directive=found_directive_name,
                    )

            # Check the imported module doesn't have any let declaration
            if len(imported_ast.execution_steps) > 0:
                first_step = imported_ast.execution_steps[0]
                if first_step:
                    raise ValuaScriptError(code=ErrorCode.GLOBAL_LET_IN_MODULE, span=first_step.span)

            ast_map[abs_import_path] = imported_ast
            # Recursively resolve imports for the newly parsed AST.
            _resolve_recursive(imported_ast, ast_map, import_stack)

        except FileNotFoundError:
            raise ValuaScriptError(code=ErrorCode.IMPORT_FILE_NOT_FOUND, span=imp.span)

    # We are done processing this file's imports, so remove it from the stack.
    import_stack.remove(current_path)


def resolve_imports(main_ast: Root) -> Dict[str, Root]:
    """
    Takes the main entry-point AST and resolves all `@import` directives.

    - Parses all imported files recursively.
    - Detects and raises errors for circular dependencies.
    - Returns a map of absolute file paths to their corresponding ASTs.
    """
    ast_map: Dict[str, Root] = {main_ast.file_path: main_ast}
    import_stack: Set[str] = set()

    _resolve_recursive(main_ast, ast_map, import_stack)

    return ast_map
