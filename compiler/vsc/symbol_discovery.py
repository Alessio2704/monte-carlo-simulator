import os
from typing import Dict, Any, Optional, Set
from .parser.parser import parse_valuascript
from .exceptions import ValuaScriptError, ErrorCode
from .functions import FUNCTION_SIGNATURES


class SymbolDiscoverer:
    """
    Scans the main AST and all imported files to discover and register
    all user-defined functions and top-level variables. It validates the
    structural integrity of the symbol table by checking for circular
    imports and illegal name redeclarations.
    """

    def __init__(self, main_ast: Dict[str, Any], main_file_path: Optional[str]):
        self.main_ast = main_ast
        self.main_file_path = main_file_path if main_file_path else "<stdin>"
        self.symbol_table = {
            "main_file_path": self.main_file_path,
            "user_defined_functions": {},
            "global_variables": {},
            "processed_files": set(),
        }
        self.visiting_stack: Set[str] = set()
        self.processed_asts: Dict[str, Dict[str, Any]] = {}

    def discover(self) -> Dict[str, Any]:
        """
        Entry point for the discovery process. It also performs final
        cross-symbol validation after discovery is complete.
        """
        self._process_file(self.main_file_path, self.main_ast, is_main_file=True)

        func_names = set(self.symbol_table["user_defined_functions"].keys())
        var_names = set(self.symbol_table["global_variables"].keys())
        collisions = func_names.intersection(var_names)

        if collisions:
            colliding_name = collisions.pop()
            var_info = self.symbol_table["global_variables"][colliding_name]
            raise ValuaScriptError(
                ErrorCode.DUPLICATE_VARIABLE,
                line=var_info["line"],
                name=colliding_name,
                message=f"L{var_info['line']}: Variable '{colliding_name}' cannot be defined because a function with the same name already exists.",
            )

        self.symbol_table["processed_asts"] = self.processed_asts

        return self.symbol_table

    def _process_file(self, file_path: str, ast: Dict[str, Any], is_main_file: bool = False, import_line: Optional[int] = None):
        """Recursively processes a file, its imports, and its symbols."""
        if file_path in self.symbol_table["processed_files"]:
            return

        if not is_main_file:
            is_module_check = any(d["name"] == "module" for d in ast.get("directives", []))
            if not is_module_check:
                raise ValuaScriptError(ErrorCode.IMPORT_NOT_A_MODULE, line=import_line, path=os.path.basename(file_path))

        self.visiting_stack.add(file_path)
        self.symbol_table["processed_files"].add(file_path)
        self.processed_asts[file_path] = ast

        if file_path == "<stdin>" and ast.get("imports"):
            first_import = ast.get("imports")[0]
            raise ValuaScriptError(ErrorCode.CANNOT_IMPORT_FROM_STDIN, line=first_import["line"])

        base_dir = os.path.dirname(file_path) if file_path != "<stdin>" else ""
        for import_node in ast.get("imports", []):
            import_rel_path = import_node["path"]
            import_abs_path = os.path.abspath(os.path.join(base_dir, import_rel_path))

            if import_abs_path in self.visiting_stack:
                raise ValuaScriptError(ErrorCode.CIRCULAR_IMPORT, line=import_node["line"], path=import_rel_path)

            try:
                with open(import_abs_path, "r") as f:
                    content = f.read()
            except FileNotFoundError:
                raise ValuaScriptError(ErrorCode.IMPORT_FILE_NOT_FOUND, line=import_node["line"], path=import_rel_path)

            imported_ast = parse_valuascript(content)
            self._process_file(import_abs_path, imported_ast, is_main_file=False, import_line=import_node["line"])

        is_module = any(d["name"] == "module" for d in ast.get("directives", []))
        execution_steps = ast.get("execution_steps", [])

        if is_module and execution_steps:
            first_offending_line = execution_steps[0]["line"]
            raise ValuaScriptError(ErrorCode.GLOBAL_LET_IN_MODULE, line=first_offending_line)

        for func_node in ast.get("function_definitions", []):
            self._register_function(func_node, file_path)

        if is_main_file:
            global_scope_vars = self.symbol_table["global_variables"]
            for assign_node in execution_steps:
                self._discover_variables_in_scope(assign_node, global_scope_vars, file_path, is_global=True)

        self.visiting_stack.remove(file_path)

    def _register_function(self, func_node: Dict[str, Any], source_path: str):
        func_name = func_node["name"]
        line = func_node["line"]

        if func_name in FUNCTION_SIGNATURES:
            raise ValuaScriptError(ErrorCode.REDEFINE_BUILTIN_FUNCTION, line=line, name=func_name)

        if func_name in self.symbol_table["user_defined_functions"]:
            existing_func = self.symbol_table["user_defined_functions"][func_name]
            raise ValuaScriptError(
                ErrorCode.DUPLICATE_FUNCTION,
                line=line,
                name=func_name,
                message=f"L{line}: Function '{func_name}' is defined more than once. It was previously defined at L{existing_func['line']} in '{os.path.basename(existing_func['source_path'])}'.",
            )

        ast_body = func_node.get("body", [])
        discovered_body_symbols = {}
        param_names = {p["name"] for p in func_node.get("params", [])}

        # Pre-populate scope with parameters for duplicate checking
        for param in func_node.get("params", []):
            param_name = param["name"]
            discovered_body_symbols[param_name] = {"name": param_name, "line": line, "source_path": source_path, "is_param": True}

        for statement in ast_body:
            if statement.get("type") in ("execution_assignment", "literal_assignment", "conditional_expression", "multi_assignment"):
                self._discover_variables_in_scope(statement, discovered_body_symbols, source_path, is_global=False, func_name=func_name)

        final_discovered_body = {name: info for name, info in discovered_body_symbols.items() if not info.get("is_param")}

        self.symbol_table["user_defined_functions"][func_name] = {
            "name": func_name,
            "params": func_node.get("params", []),
            "return_type": func_node.get("return_type"),
            "docstring": func_node.get("docstring"),
            "line": line,
            "source_path": source_path,
            "ast_body": ast_body,
            "discovered_body": final_discovered_body,
        }

    def _discover_variables_in_scope(self, assign_node: Dict[str, Any], scope_dict: Dict, source_path: str, is_global: bool, func_name: Optional[str] = None):
        var_names = assign_node.get("results") or [assign_node.get("result")]
        line = assign_node["line"]

        if len(var_names) != len(set(var_names)):
            seen = set()
            for name in var_names:
                if name in seen:
                    dup_name = name
                    break
                seen.add(name)
            error_code = ErrorCode.DUPLICATE_VARIABLE if is_global else ErrorCode.DUPLICATE_VARIABLE_IN_FUNC
            raise ValuaScriptError(error_code, line=line, name=dup_name, func_name=func_name)

        for name in var_names:
            if name in scope_dict:
                if is_global:
                    raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE, line=line, name=name)
                else:
                    raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE_IN_FUNC, line=line, name=name, func_name=func_name)
            scope_dict[name] = {
                "name": name,
                "line": line,
                "source_path": source_path,
            }


def discover_symbols(ast: Dict[str, Any], file_path: Optional[str]) -> Dict[str, Any]:
    """
    High-level entry point for the symbol discovery and validation stage.
    """
    discoverer = SymbolDiscoverer(ast, file_path)
    return discoverer.discover()
