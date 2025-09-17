import os
from typing import Dict, Any, List, Optional, Union
from collections import deque

from .data_structures import FileSemanticModel, Scope, Symbol, VariableSymbol, FunctionSymbol, FunctionParameter, ExpressionNode, Location, ConditionalNode
from .parser import parse_valuascript, _StringLiteral
from .exceptions import ValuaScriptError, ErrorCode
from .functions import FUNCTION_SIGNATURES
from lark import Token


class SemanticAnalyzer:
    """
    Builds and validates the Semantic Model from the raw AST.
    This class handles symbol discovery, import resolution, name resolution,
    type inference, and other semantic checks.
    """

    def __init__(self, ast: Dict[str, Any], file_path: str, processed_files: Optional[Dict[str, FileSemanticModel]] = None, visiting_stack: Optional[set] = None):
        self.ast = ast
        self.file_path = file_path
        self.model = FileSemanticModel(file_path=self.file_path)
        self.current_scope = self.model.global_scope

        self.processed_files = processed_files if processed_files is not None else {}
        self.visiting_stack = visiting_stack if visiting_stack is not None else set()

    def analyze(self) -> FileSemanticModel:
        """Main entry point to build and validate the model."""
        self.processed_files[self.file_path] = self.model
        self.visiting_stack.add(self.file_path)

        self._process_directives()
        self._process_imports()
        self._discover_symbols()
        self._validate_model()

        self.visiting_stack.remove(self.file_path)
        return self.model

    def _process_directives(self):
        for directive_node in self.ast.get("directives", []):
            self.model.directives[directive_node["name"]] = directive_node
            if directive_node["name"] == "module":
                self.model.is_module = True

    def _process_imports(self):
        base_dir = os.path.dirname(self.file_path)
        for import_node in self.ast.get("imports", []):
            import_path = os.path.abspath(os.path.join(base_dir, import_node["path"]))

            if import_path in self.visiting_stack:
                raise ValuaScriptError(ErrorCode.CIRCULAR_IMPORT, line=import_node["line"], path=import_node["path"])

            imported_model = self.processed_files.get(import_path)
            if not imported_model:
                try:
                    with open(import_path, "r") as f:
                        content = f.read()
                except FileNotFoundError:
                    raise ValuaScriptError(ErrorCode.IMPORT_FILE_NOT_FOUND, line=import_node["line"], path=import_node["path"])

                imported_ast = parse_valuascript(content)
                analyzer = SemanticAnalyzer(imported_ast, import_path, self.processed_files, self.visiting_stack)
                imported_model = analyzer.analyze()

            if not imported_model.is_module:
                raise ValuaScriptError(ErrorCode.IMPORT_NOT_A_MODULE, line=import_node["line"], path=import_node["path"])

            for name, symbol in imported_model.global_scope.symbols.items():
                if isinstance(symbol, FunctionSymbol):
                    if name in self.current_scope.symbols:
                        existing_symbol = self.current_scope.symbols[name]
                        if isinstance(existing_symbol, FunctionSymbol) and existing_symbol.location != symbol.location:
                            raise ValuaScriptError(ErrorCode.FUNCTION_NAME_COLLISION, line=symbol.location.line, name=name, path=import_node["path"])
                    else:
                        self.current_scope.symbols[name] = symbol

    def _discover_symbols(self):
        """First pass: discover all function and variable declarations."""
        for func_node in self.ast.get("function_definitions", []):
            self._add_function_symbol(func_node)

        if self.model.is_module and self.ast.get("execution_steps"):
            line = self.ast["execution_steps"][0]["line"]
            raise ValuaScriptError(ErrorCode.GLOBAL_LET_IN_MODULE, line=line)

        for assign_node in self.ast.get("execution_steps", []):
            self._add_variable_symbol(assign_node, self.current_scope)

    def _add_function_symbol(self, func_node: Dict[str, Any]):
        name, line = func_node["name"], func_node["line"]
        location = Location(self.file_path, line, 1)

        if name in self.current_scope.symbols or name in FUNCTION_SIGNATURES:
            if name in FUNCTION_SIGNATURES:
                raise ValuaScriptError(ErrorCode.REDEFINE_BUILTIN_FUNCTION, line=line, name=name)
            raise ValuaScriptError(ErrorCode.DUPLICATE_FUNCTION, line=line, name=name)

        params = [FunctionParameter(name=p["name"], type=p["type"], location=Location(self.file_path, line, 1)) for p in func_node["params"]]

        func_symbol = FunctionSymbol(name=name, location=location, parameters=params, return_type=func_node["return_type"], docstring=func_node.get("docstring"))
        func_symbol.body = Scope(parent=self.current_scope)

        # FIX: Store the raw AST body for later processing
        func_symbol.ast_body = func_node.get("body", [])

        return_node = next((n for n in func_symbol.ast_body if n.get("type") == "return_statement"), None)
        if return_node:
            return_value = return_node.get("value") or return_node.get("values")
            func_symbol.return_node = ExpressionNode(raw_node=return_value)

        for p in params:
            param_symbol = VariableSymbol(name=p.name, location=p.location, value_node=None)
            param_symbol.inferred_type = p.type
            func_symbol.body.symbols[p.name] = param_symbol

        # FIX: Now discover local variables and add them to the function's body scope
        for body_node in func_symbol.ast_body:
            if body_node.get("type") != "return_statement":
                self._add_variable_symbol(body_node, func_symbol.body)

        self.model.global_scope.symbols[name] = func_symbol

    def _add_variable_symbol(self, assign_node: Dict[str, Any], scope: Scope):
        line = assign_node["line"]
        var_names = assign_node.get("results") or [assign_node.get("result")]

        if len(set(var_names)) != len(var_names):
            raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE, line=line, name="a variable in the same assignment")

        for name in var_names:
            if name in scope.symbols:
                raise ValuaScriptError(ErrorCode.DUPLICATE_VARIABLE_IN_FUNC if scope.parent else ErrorCode.DUPLICATE_VARIABLE, line=line, name=name, func_name=self._get_func_context(scope))

            location = Location(self.file_path, line, 1)
            expression_node = ExpressionNode(raw_node=assign_node)
            var_symbol = VariableSymbol(name=name, location=location, value_node=expression_node)
            scope.symbols[name] = var_symbol

    def _get_func_context(self, scope: Scope) -> Optional[str]:
        if not scope.parent:
            return None
        for symbol in scope.parent.symbols.values():
            if isinstance(symbol, FunctionSymbol) and symbol.body == scope:
                return symbol.name
        return None

    def _get_symbol_from_scope(self, name: str, scope: Scope) -> Optional[Symbol]:
        while scope:
            if name in scope.symbols:
                return scope.symbols[name]
            scope = scope.parent
        return None

    def _validate_model(self):
        """Second pass: perform type checking and other semantic validations."""
        self._check_recursion()
        self._validate_scope(self.model.global_scope)

    def _validate_scope(self, scope: Scope):
        # The order of validation is critical. We must validate parent scopes
        # before child scopes (functions).
        for symbol in scope.symbols.values():
            if isinstance(symbol, VariableSymbol) and symbol.value_node:
                value_node = symbol.value_node
                raw_node = value_node.raw_node

                inferred_type = self._infer_expression_type(raw_node, scope)
                is_stochastic = self._is_expression_stochastic(raw_node, scope)

                symbol.inferred_type = inferred_type
                symbol.is_stochastic = is_stochastic
                value_node.inferred_type = inferred_type
                value_node.is_stochastic = is_stochastic

                if isinstance(inferred_type, list):
                    var_names = raw_node["results"]
                    for i, name in enumerate(var_names):
                        var_sym = self._get_symbol_from_scope(name, scope)
                        if var_sym:
                            var_sym.inferred_type = inferred_type[i]
                            var_sym.is_stochastic = is_stochastic

        # Now that the current scope is fully typed, validate its functions
        for symbol in scope.symbols.values():
            if isinstance(symbol, FunctionSymbol):
                symbol.inferred_type = symbol.return_type
                # Recursively validate the function's inner scope
                self._validate_scope(symbol.body)
                self._validate_function_return(symbol)
                if symbol.return_node:
                    symbol.is_stochastic = self._is_expression_stochastic(symbol.return_node.raw_node, symbol.body)

    def _is_expression_stochastic(self, node: Any, scope: Scope) -> bool:
        """Recursively checks if an expression is stochastic."""
        if isinstance(node, Token):
            symbol = self._get_symbol_from_scope(node.value, scope)
            return symbol.is_stochastic if symbol else False

        if not isinstance(node, dict):
            return False

        func_name = node.get("function")
        if func_name:
            if FUNCTION_SIGNATURES.get(func_name, {}).get("is_stochastic"):
                return True
            udf_symbol = self._get_symbol_from_scope(func_name, self.model.global_scope)
            if isinstance(udf_symbol, FunctionSymbol) and udf_symbol.is_stochastic:
                return True

        if "args" in node:
            if any(self._is_expression_stochastic(arg, scope) for arg in node["args"]):
                return True

        if node.get("type") == "conditional_expression":
            if self._is_expression_stochastic(node["then_expr"], scope) or self._is_expression_stochastic(node["else_expr"], scope):
                return True

        return False

    def _infer_expression_type(self, node: Any, scope: Scope) -> Union[str, List[str]]:
        line = node.get("line", 1) if isinstance(node, dict) else 1

        if isinstance(node, Token):
            symbol = self._get_symbol_from_scope(node.value, scope)
            if not symbol:
                raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE_IN_FUNC, line=line, name=node.value, func_name=self._get_func_context(scope) or "global scope")
            return symbol.inferred_type

        if isinstance(node, (int, float)):
            return "scalar"
        if isinstance(node, bool):
            return "boolean"
        if isinstance(node, _StringLiteral):
            return "string"
        if isinstance(node, list):
            if all(isinstance(item, Token) for item in node):
                return [self._infer_expression_type(item, scope) for item in node]
            for item in node:
                item_type = self._infer_expression_type(item, scope)
                if item_type not in ("scalar", "any"):
                    raise ValuaScriptError(ErrorCode.INVALID_ITEM_IN_VECTOR, line=line, value=str(item), name="vector literal")
            return "vector"

        if isinstance(node, dict):
            if node.get("_is_tuple_return"):
                return [self._infer_expression_type(v, scope) for v in node["values"]]

            node_type = node.get("type")

            if node_type == "conditional_expression":
                cond_type = self._infer_expression_type(node["condition"], scope)
                if cond_type != "boolean":
                    raise ValuaScriptError(ErrorCode.IF_CONDITION_NOT_BOOLEAN, line=line, provided=cond_type)
                then_type = self._infer_expression_type(node["then_expr"], scope)
                else_type = self._infer_expression_type(node["else_expr"], scope)
                if then_type != else_type:
                    raise ValuaScriptError(ErrorCode.IF_ELSE_TYPE_MISMATCH, line=line, then_type=str(then_type), else_type=str(else_type))
                return then_type

            func_name = node.get("function")
            if not func_name:
                return self._infer_expression_type(node.get("value"), scope)

            all_funcs = {**FUNCTION_SIGNATURES}
            for s_name, symbol in self.model.global_scope.symbols.items():
                if isinstance(symbol, FunctionSymbol):
                    all_funcs[s_name] = {"arg_types": [p.type for p in symbol.parameters], "return_type": symbol.return_type, "variadic": False}

            sig = all_funcs.get(func_name)
            if not sig:
                raise ValuaScriptError(ErrorCode.UNKNOWN_FUNCTION, line=line, name=func_name)

            args = node.get("args", [])
            inferred_arg_types = [self._infer_expression_type(arg, scope) for arg in args]

            if not sig.get("variadic", False):
                if len(inferred_arg_types) != len(sig["arg_types"]):
                    raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=func_name, expected=len(sig["arg_types"]), provided=len(inferred_arg_types))
                for i, expected in enumerate(sig["arg_types"]):
                    actual = inferred_arg_types[i]
                    if expected != "any" and actual != "any" and expected != actual:
                        raise ValuaScriptError(ErrorCode.ARGUMENT_TYPE_MISMATCH, line=line, arg_num=i + 1, name=func_name, expected=expected, provided=actual)

            ret_type = sig["return_type"]
            return ret_type(inferred_arg_types) if callable(ret_type) else ret_type

        return "any"

    def _validate_function_return(self, func_symbol: FunctionSymbol):
        if not func_symbol.return_node:
            if func_symbol.ast_body:
                raise ValuaScriptError(ErrorCode.MISSING_RETURN_STATEMENT, line=func_symbol.location.line, name=func_symbol.name)
            return

        expected_type = func_symbol.return_type
        return_node = func_symbol.return_node

        # FIX: Enrich the return_node with its own type and stochasticity info
        actual_type = self._infer_expression_type(return_node.raw_node, func_symbol.body)
        is_stochastic = self._is_expression_stochastic(return_node.raw_node, func_symbol.body)
        return_node.inferred_type = actual_type
        return_node.is_stochastic = is_stochastic

        if actual_type != expected_type:
            raise ValuaScriptError(ErrorCode.RETURN_TYPE_MISMATCH, line=func_symbol.location.line, name=func_symbol.name, provided=str(actual_type), expected=str(expected_type))

    def _check_recursion(self):
        """Builds a call graph of all UDFs and checks for cycles."""
        call_graph = {name: set() for name, sym in self.model.global_scope.symbols.items() if isinstance(sym, FunctionSymbol)}

        for func_name, func_symbol in self.model.global_scope.symbols.items():
            if not isinstance(func_symbol, FunctionSymbol):
                continue

            func_ast_node = next((n for n in self.ast.get("function_definitions", []) if n["name"] == func_name), None)
            if not func_ast_node:
                continue

            q = deque(func_ast_node.get("body", []))
            visited_nodes = set()
            while q:
                node = q.popleft()
                if not isinstance(node, dict) or id(node) in visited_nodes:
                    continue
                visited_nodes.add(id(node))

                called_func = node.get("function")
                if called_func in call_graph:
                    call_graph[func_name].add(called_func)

                for val in node.values():
                    if isinstance(val, dict):
                        q.append(val)
                    elif isinstance(val, list):
                        q.extend(val)

        visiting, visited = set(), set()
        for func_name in sorted(list(call_graph.keys())):
            if func_name not in visited:
                path = []
                if self._has_cycle_util(func_name, call_graph, visiting, visited, path):
                    cycle_path_str = " -> ".join(path)
                    raise ValuaScriptError(ErrorCode.RECURSIVE_CALL_DETECTED, path=cycle_path_str)

    def _has_cycle_util(self, node, graph, visiting, visited, path):
        visiting.add(node)
        path.append(node)
        for neighbor in sorted(list(graph.get(node, []))):
            if neighbor in visiting:
                path.append(neighbor)
                return True
            if neighbor not in visited:
                if self._has_cycle_util(neighbor, graph, visiting, visited, path):
                    return True
        visiting.remove(node)
        visited.add(node)
        path.pop()
        return False


def build_and_validate_model(ast: Dict[str, Any], file_path: str) -> FileSemanticModel:
    """
    Orchestrates the creation and validation of the semantic model.
    This is the main entry point for this compilation stage.
    """
    analyzer = SemanticAnalyzer(ast, file_path)
    return analyzer.analyze()
