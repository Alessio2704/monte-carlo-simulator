from typing import Dict, Any, List, Tuple, Union, Set
from lark import Token

from .parser import _StringLiteral
from .exceptions import ValuaScriptError, ErrorCode
from .functions import FUNCTION_SIGNATURES


class TypeInferrer:
    """
    Performs Phase 3 of compilation: Type Inference and Stochasticity Tainting.
    This class takes a raw symbol table, infers the type of every variable
    and expression, and determines if it is "stochastic" (i.e., its value can
    change between simulation trials).

    This process is non-validating; it assumes the code structure is sound
    and focuses only on annotating the symbol table with this new information.
    """

    def __init__(self, symbol_table: Dict[str, Any]):
        self.symbol_table = symbol_table
        self.all_signatures = self._build_combined_signatures()
        self.processed_vars: Set[str] = set()

    def infer(self) -> Dict[str, Any]:
        """
        Main entry point. Enriches the entire symbol table with type and
        stochasticity information using a multi-pass approach.
        """
        # --- PASS 1: Iteratively determine UDF stochasticity ---
        changed = True
        while changed:
            changed = False
            for func_name, func_info in self.symbol_table["user_defined_functions"].items():
                param_scope = {p["name"]: {"inferred_type": p["type"], "is_stochastic": False} for p in func_info["params"]}
                body_scope = {**param_scope, **func_info["discovered_body"]}
                new_stochastic_state = self._is_udf_body_stochastic(func_info, body_scope)
                if self.all_signatures[func_name].get("is_stochastic") != new_stochastic_state:
                    changed = True
                func_info["is_stochastic"] = new_stochastic_state
                self.all_signatures[func_name]["is_stochastic"] = new_stochastic_state

        # --- PASS 2: Process all scopes with the finalized signatures ---
        main_ast = self.symbol_table["processed_asts"][self.symbol_table["main_file_path"]]
        global_execution_steps = main_ast.get("execution_steps", [])
        self._process_scope(global_execution_steps, self.symbol_table["global_variables"])

        for func_name, func_info in self.symbol_table["user_defined_functions"].items():
            self.processed_vars.clear()
            param_scope = {}
            for param in func_info["params"]:
                param_name = param["name"]
                param_scope[param_name] = {"inferred_type": param["type"], "is_stochastic": False}
                self.processed_vars.add(param_name)
            self._process_scope(func_info["ast_body"], func_info["discovered_body"], param_scope)

        return self.symbol_table

    def _is_udf_body_stochastic(self, func_info: Dict, local_scope: Dict) -> bool:
        return_node = next((s for s in func_info["ast_body"] if s.get("type") == "return_statement"), None)
        if not return_node:
            return False

        temp_scope_for_check = local_scope.copy()
        for stmt in func_info["ast_body"]:
            if stmt.get("type") in ("execution_assignment", "literal_assignment", "conditional_expression", "multi_assignment"):
                var_names = stmt.get("results") or [stmt.get("result")]
                inferred_type, is_stochastic = self._infer_expression_details(stmt, temp_scope_for_check)
                for i, name in enumerate(var_names):
                    final_type = inferred_type[i] if isinstance(inferred_type, list) else inferred_type
                    temp_scope_for_check[name] = {"inferred_type": final_type, "is_stochastic": is_stochastic}

        _, is_stochastic = self._infer_expression_details(return_node.get("value") or return_node.get("values"), temp_scope_for_check)
        return is_stochastic

    def _process_scope(self, execution_steps: List[Dict], symbol_scope: Dict, local_context: Dict = None):
        if local_context is None:
            local_context = self.symbol_table["global_variables"]

        for step in execution_steps:
            if step.get("type") in ("execution_assignment", "literal_assignment", "conditional_expression", "multi_assignment"):
                inferred_type, is_stochastic = self._infer_expression_details(step, local_context)
                var_names = step.get("results") or [step.get("result")]
                for i, name in enumerate(var_names):
                    symbol_entry = symbol_scope.get(name)
                    if symbol_entry:
                        final_type = inferred_type[i] if isinstance(inferred_type, list) else inferred_type
                        symbol_entry["inferred_type"] = final_type
                        symbol_entry["is_stochastic"] = is_stochastic
                        local_context[name] = {"inferred_type": final_type, "is_stochastic": is_stochastic}
                        self.processed_vars.add(name)

    def _infer_expression_details(self, node: Any, scope: Dict) -> Tuple[Union[str, List[str]], bool]:
        if isinstance(node, bool):
            return "boolean", False
        if isinstance(node, (int, float)):
            return "scalar", False

        if isinstance(node, _StringLiteral):
            return "string", False

        if isinstance(node, list):
            item_details = [self._infer_expression_details(item, scope) for item in node]
            is_stochastic = any(detail[1] for detail in item_details)
            inferred_types = [detail[0] for detail in item_details]
            return inferred_types, is_stochastic

        if isinstance(node, Token):
            if node.value not in scope:
                return "any", False
            var_info = scope[node.value]
            return var_info.get("inferred_type", "any"), var_info.get("is_stochastic", False)

        if not isinstance(node, dict):
            return "any", False

        if node.get("_is_vector_literal"):
            item_details = [self._infer_expression_details(item, scope) for item in node.get("items", [])]
            is_stochastic = any(detail[1] for detail in item_details)
            return "vector", is_stochastic

        expression_stochasticity = False
        inferred_type = "any"

        if "function" not in node and "value" in node:
            return self._infer_expression_details(node["value"], scope)

        args = node.get("args", [])
        arg_details = [self._infer_expression_details(arg, scope) for arg in args]
        arg_types = [details[0] for details in arg_details]
        if any(details[1] for details in arg_details):
            expression_stochasticity = True

        if node.get("type") == "conditional_expression":
            cond_type, cond_stochastic = self._infer_expression_details(node["condition"], scope)
            then_type, then_stochastic = self._infer_expression_details(node["then_expr"], scope)
            else_type, else_stochastic = self._infer_expression_details(node["else_expr"], scope)
            expression_stochasticity = expression_stochasticity or cond_stochastic or then_stochastic or else_stochastic
            inferred_type = then_type
        elif "function" in node:
            func_name = node["function"]
            sig = self.all_signatures.get(func_name)
            if not sig:
                return "any", expression_stochasticity

            if sig.get("is_stochastic", False):
                expression_stochasticity = True

            return_type_rule = sig["return_type"]
            inferred_type = return_type_rule(arg_types) if callable(return_type_rule) else return_type_rule

        return inferred_type, expression_stochasticity

    def _build_combined_signatures(self) -> Dict:
        udf_signatures = {}
        for name, fdef in self.symbol_table["user_defined_functions"].items():
            udf_signatures[name] = {"variadic": False, "arg_types": [p["type"] for p in fdef["params"]], "return_type": fdef["return_type"], "is_stochastic": fdef.get("is_stochastic", False)}
        return {**FUNCTION_SIGNATURES, **udf_signatures}


def infer_types_and_taint(symbol_table: Dict[str, Any]) -> Dict[str, Any]:
    inferrer = TypeInferrer(symbol_table)
    return inferrer.infer()
