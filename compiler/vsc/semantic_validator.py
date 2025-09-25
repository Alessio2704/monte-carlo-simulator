import os
from typing import Dict, Any, List, Union
from lark import Token

from .parser import _StringLiteral
from .exceptions import ValuaScriptError, ErrorCode
from .config import DIRECTIVE_CONFIG


class SemanticValidator:
    """
    Performs Phase 4 of compilation: Semantic Validation.
    This class consumes the enriched symbol table from the TypeInferrer and
    validates it against the rules of the ValuaScript language.

    It is a destructive process in the sense that it will raise a
    ValuaScriptError and halt compilation if any rule is violated.
    """

    def __init__(self, enriched_symbol_table: Dict[str, Any]):
        self.table = enriched_symbol_table
        self.all_signatures = self.table["all_signatures"]
        main_ast = self.table["processed_asts"][self.table["main_file_path"]]
        self.is_main_file_a_module = any(d["name"] == "module" for d in main_ast.get("directives", []))
        self.current_scope_name = "global"

    def validate(self):
        """Main entry point for the validation process."""
        self._validate_directives()
        self._check_for_recursion()

        main_ast = self.table["processed_asts"][self.table["main_file_path"]]
        global_scope = self.table["global_variables"]
        for step in main_ast.get("execution_steps", []):
            self._validate_assignment_arity(step, global_scope)  # Check arity
            self._validate_expression(step, global_scope)  # Then check contents

        for func_name, func_info in self.table["user_defined_functions"].items():
            self.current_scope_name = func_name
            param_scope = {p["name"]: {"inferred_type": p["type"]} for p in func_info["params"]}
            local_scope = {**param_scope, **func_info["discovered_body"]}

            has_return_statement = False
            for step in func_info["ast_body"]:
                self._validate_assignment_arity(step, local_scope)  # Check arity
                self._validate_expression(step, local_scope)  # Then check contents
                if step.get("type") == "return_statement":
                    has_return_statement = True

            if not has_return_statement:
                raise ValuaScriptError(ErrorCode.MISSING_RETURN_STATEMENT, line=func_info["line"], name=func_name)

        return self.table

    def _validate_assignment_arity(self, step: Dict[str, Any], scope: Dict):
        """
        Checks if the number of variables on the LHS of an assignment matches
        the number of values produced by the RHS.
        """
        # This function only cares about assignment statements
        if step.get("type") not in ("execution_assignment", "literal_assignment", "conditional_expression", "multi_assignment"):
            return

        lhs_vars = step.get("results") or ([step.get("result")] if step.get("result") else [])
        if not lhs_vars:
            return

        lhs_count = len(lhs_vars)

        # The node itself represents the RHS expression in our AST structure
        rhs_type = self._get_node_type(step, scope)
        rhs_count = len(rhs_type) if isinstance(rhs_type, list) else 1

        if lhs_count != rhs_count:
            raise ValuaScriptError(
                ErrorCode.ASSIGNMENT_ERROR,
                line=step["line"],
                lhs_count=lhs_count,
                rhs_count=rhs_count,
                message=f"L{step['line']}: Assignment mismatch. Expression returns {rhs_count} value(s), but {lhs_count} variable(s) are provided.",
            )

    def _validate_directives(self):
        main_file_path = self.table["main_file_path"]
        main_ast = self.table["processed_asts"][main_file_path]
        directives = {d["name"]: d for d in main_ast.get("directives", [])}
        global_vars = self.table["global_variables"]

        if not self.is_main_file_a_module:
            for name, config in DIRECTIVE_CONFIG.items():
                if name in ["import", "module"]:
                    continue
                is_req = config["required"]({}) if callable(config["required"]) else config["required"]
                if is_req and name not in directives:
                    error_code = ErrorCode[f"MISSING_{name.upper()}_DIRECTIVE"]
                    raise ValuaScriptError(error_code, file_path=os.path.basename(main_file_path))

        for name, d in directives.items():
            config = DIRECTIVE_CONFIG.get(name)
            if not config:
                continue
            if self.is_main_file_a_module and not config["allowed_in_module"]:
                raise ValuaScriptError(ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, line=d["line"], name=name)

            value_node = d.get("value")
            expected_py_type = config["value_type"]

            if name == "output":
                output_var_name = str(value_node)
                if output_var_name not in global_vars:
                    raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, line=d["line"], name=output_var_name, context="the @output directive")

            valid = False
            if expected_py_type == str and isinstance(value_node, (_StringLiteral, Token)):
                valid = True
            elif expected_py_type == int and isinstance(value_node, int):
                valid = True
            elif expected_py_type == bool and isinstance(value_node, bool):
                valid = True

            if not valid:
                raise ValuaScriptError(ErrorCode.INVALID_DIRECTIVE_VALUE, line=d["line"], error_msg=config["error_type"])

    def _validate_expression(self, node: Any, scope: Dict):
        if isinstance(node, Token):
            line = node.line if hasattr(node, "line") else -1
            if node.value not in scope:
                context_str = "the global scope" if self.current_scope_name == "global" else f"function '{self.current_scope_name}'"
                raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, line=line, name=node.value, context=context_str)
            return

        if not isinstance(node, dict):
            return

        if node.get("_is_vector_literal"):
            items, line = node.get("items", []), node.get("line", -1)
            if len(items) > 1:
                item_types = {self._get_node_type(item, scope) for item in items}
                if len(item_types) > 1:
                    raise ValuaScriptError(ErrorCode.MIXED_TYPES_IN_VECTOR, line=line, found_types=", ".join(sorted(list(item_types))))
            for item in items:
                if self._get_node_type(item, scope) != "scalar":
                    raise ValuaScriptError(ErrorCode.INVALID_ITEM_TYPE_IN_VECTOR, line=line, type=self._get_node_type(item, scope))

        for arg in node.get("args", []):
            self._validate_expression(arg, scope)
        for key in ["condition", "then_expr", "else_expr", "value"]:
            if key in node:
                self._validate_expression(node[key], scope)

        node_type, line = node.get("type"), node.get("line", -1)

        if node_type == "conditional_expression":
            cond_type = self._get_node_type(node["condition"], scope)
            if cond_type != "boolean":
                raise ValuaScriptError(ErrorCode.IF_CONDITION_NOT_BOOLEAN, line=line, provided=cond_type)
            then_type, else_type = self._get_node_type(node["then_expr"], scope), self._get_node_type(node["else_expr"], scope)
            if then_type != else_type:
                raise ValuaScriptError(ErrorCode.IF_ELSE_TYPE_MISMATCH, line=line, then_type=then_type, else_type=else_type)
        elif node_type == "return_statement":
            func_def = self.table["user_defined_functions"][self.current_scope_name]
            expected_type, return_value = func_def["return_type"], node.get("value") or node.get("values")
            actual_type = self._get_node_type(return_value, scope)
            if actual_type != expected_type:
                raise ValuaScriptError(ErrorCode.RETURN_TYPE_MISMATCH, line=line, name=self.current_scope_name, provided=str(actual_type), expected=str(expected_type))
        elif "function" in node:
            func_name, arg_nodes = node["function"], node.get("args", [])
            sig = self.all_signatures.get(func_name)
            if not sig:
                raise ValuaScriptError(ErrorCode.UNKNOWN_FUNCTION, line=line, name=func_name)

            MATH_OPERATORS = {"add": "+", "subtract": "-", "multiply": "*", "divide": "/", "power": "^"}
            if func_name in MATH_OPERATORS:
                for arg in arg_nodes:
                    arg_type = self._get_node_type(arg, scope)
                    if arg_type not in ("scalar", "vector", "any"):
                        raise ValuaScriptError(ErrorCode.OPERATOR_TYPE_MISMATCH, line=line, op=MATH_OPERATORS[func_name], provided_type=arg_type)
                return

            if not sig.get("variadic", False):
                if len(arg_nodes) != len(sig["arg_types"]):
                    raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=func_name, expected=len(sig["arg_types"]), provided=len(arg_nodes))
                for i, arg_node in enumerate(arg_nodes):
                    expected, actual = sig["arg_types"][i], self._get_node_type(arg_node, scope)
                    if expected != "any" and actual != "any" and actual != expected:
                        raise ValuaScriptError(ErrorCode.ARGUMENT_TYPE_MISMATCH, line=line, arg_num=i + 1, name=func_name, expected=expected, provided=actual)
            elif sig["arg_types"]:
                expected = sig["arg_types"][0]
                if expected != "any":
                    for i, arg_node in enumerate(arg_nodes):
                        actual = self._get_node_type(arg_node, scope)
                        if actual != "any" and actual != expected:
                            raise ValuaScriptError(ErrorCode.ARGUMENT_TYPE_MISMATCH, line=line, arg_num=i + 1, name=func_name, expected=expected, provided=actual)

    def _get_node_type(self, node: Any, scope: Dict) -> Union[str, List[str]]:
        if isinstance(node, bool):
            return "boolean"
        if isinstance(node, (int, float)):
            return "scalar"
        if isinstance(node, Token):
            return scope.get(node.value, {}).get("inferred_type", "any")
        if isinstance(node, _StringLiteral):
            return "string"
        if isinstance(node, list):
            return [self._get_node_type(n, scope) for n in node]
        if not isinstance(node, dict):
            return "any"
        if node.get("_is_vector_literal"):
            return "vector"
        if node.get("type") == "conditional_expression":
            return self._get_node_type(node["then_expr"], scope)
        if "function" in node:
            func_name = node["function"]
            sig = self.all_signatures.get(func_name)
            if not sig:
                return "any"
            return_type_rule = sig["return_type"]
            if callable(return_type_rule):
                arg_types = [self._get_node_type(arg, scope) for arg in node.get("args", [])]
                return return_type_rule(arg_types)
            return return_type_rule
        return "any"

    def _check_for_recursion(self):
        call_graph = {name: set() for name in self.table["user_defined_functions"]}
        for func_name, func_info in self.table["user_defined_functions"].items():
            q = list(func_info["ast_body"])
            visited_nodes = set()
            while q:
                node = q.pop(0)
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


def validate_semantics(enriched_symbol_table: Dict[str, Any]) -> Dict[str, Any]:
    validator = SemanticValidator(enriched_symbol_table)
    return validator.validate()
