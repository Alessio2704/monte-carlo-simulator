from typing import List, Dict, Any, Union
from .data_structures import FileSemanticModel, Scope, Symbol, VariableSymbol, FunctionSymbol, ExpressionNode
from .parser import _StringLiteral
from lark import Token


class IRGenerator:
    """
    Generates a linear Intermediate Representation (IR) from a validated semantic model.
    The primary responsibility of this class is to inline all user-defined functions.
    """

    def __init__(self, model: FileSemanticModel):
        self.model = model
        self.ir_steps: List[Dict[str, Any]] = []
        self.udf_call_count: Dict[str, int] = {}
        self.temp_var_count = 0

    def generate(self) -> List[Dict[str, Any]]:
        """Generates the full IR for the global scope."""
        self._process_scope(self.model.global_scope)
        return self.ir_steps

    def _process_scope(self, scope: Scope):
        # We need to process variables in the order they were declared.
        # The AST provides this order.
        execution_order = [step for step in self.model.ast.get("execution_steps", []) if (step.get("result") or (step.get("results") and step.get("results")[0])) in scope.symbols]

        for assignment_node in execution_order:
            self._generate_ir_for_node(assignment_node, scope)

    def _generate_ir_for_node(self, node: Dict[str, Any], scope: Scope) -> Union[Token, Dict, Any]:
        """
        Recursively processes an AST node to generate IR steps.
        If the node is a UDF call, it triggers inlining.
        Returns the final "value" of the expression (e.g., a variable Token or a literal).
        """
        # Base case: Literals and existing variables
        if isinstance(node, (Token, _StringLiteral, int, float, bool, list)):
            return node

        if not isinstance(node, dict):
            return node

        # Lift nested UDF calls out of expressions first.
        node = self._lift_nested_udf_calls(node, scope)

        func_name = node.get("function")
        if func_name:
            # Check if it's a UDF that needs inlining
            symbol = self.model.global_scope.symbols.get(func_name)
            if isinstance(symbol, FunctionSymbol):
                # The _inline_udf_call method now handles adding all necessary steps to the IR.
                # We just need a placeholder return value to satisfy the recursive algorithm.
                self._inline_udf_call(node, symbol, scope)
                self.temp_var_count += 1
                return Token("CNAME", f"__temp_inline_{self.temp_var_count}")

        # For built-in functions or regular assignments, add the step
        # after processing its arguments recursively.
        processed_node = node.copy()
        if "args" in processed_node:
            processed_node["args"] = [self._generate_ir_for_node(arg, scope) for arg in node["args"]]

        if processed_node.get("type") == "conditional_expression":
            processed_node["condition"] = self._generate_ir_for_node(processed_node["condition"], scope)
            processed_node["then_expr"] = self._generate_ir_for_node(processed_node["then_expr"], scope)
            processed_node["else_expr"] = self._generate_ir_for_node(processed_node["else_expr"], scope)

        # If this node represents a top-level assignment, add it to the IR.
        # Otherwise, it's a nested expression, so we just return it.
        if "result" in processed_node or "results" in processed_node:
            self.ir_steps.append(processed_node)

        return processed_node

    def _lift_nested_udf_calls(self, node: Dict, scope: Scope) -> Dict:
        """Pre-pass to hoist nested UDF calls into their own temporary variables."""
        if not isinstance(node, dict):
            return node

        if "args" in node:
            new_args = []
            for arg in node["args"]:
                new_args.append(self._generate_ir_for_node(arg, scope))
            node["args"] = new_args

        if node.get("type") == "conditional_expression":
            node["condition"] = self._generate_ir_for_node(node["condition"], scope)
            node["then_expr"] = self._generate_ir_for_node(node["then_expr"], scope)
            node["else_expr"] = self._generate_ir_for_node(node["else_expr"], scope)

        return node

    def _inline_udf_call(self, call_node: Dict[str, Any], func_symbol: FunctionSymbol, scope: Scope):
        """Replaces a UDF call with its body, mangling names and adding steps to the IR."""
        self.udf_call_count[func_symbol.name] = self.udf_call_count.get(func_symbol.name, 0) + 1
        call_id = self.udf_call_count[func_symbol.name]
        mangling_prefix = f"__{func_symbol.name}_{call_id}__"

        param_map = {}
        for i, param in enumerate(func_symbol.parameters):
            mangled_name = f"{mangling_prefix}{param.name}"
            arg_value = self._generate_ir_for_node(call_node["args"][i], scope)

            self.ir_steps.append(
                {
                    "type": "execution_assignment",
                    "result": mangled_name,
                    "function": "identity",
                    "args": [arg_value],
                    "line": call_node["line"],
                }
            )
            param_map[param.name] = Token("CNAME", mangled_name)

        func_ast_body = func_symbol.ast_body

        for body_stmt_node in func_ast_body:
            # FIX: The core of the bug fix is here.
            # We must distinguish between a return statement and a regular assignment.

            is_return = body_stmt_node.get("type") == "return_statement"
            mangled_stmt = self._mangle_node(body_stmt_node, mangling_prefix, param_map)

            if is_return:
                # This is the return statement. Its value is used to create the FINAL
                # assignment for the original calling variable.
                # The return statement itself is NOT added to the IR.
                original_results = call_node.get("results") or [call_node.get("result")]
                return_values = mangled_stmt.get("values") or [mangled_stmt.get("value")]

                if len(original_results) > 1:  # Multi-assignment
                    for i, res_name in enumerate(original_results):
                        self.ir_steps.append({"type": "execution_assignment", "result": res_name, "function": "identity", "args": [return_values[i]], "line": call_node["line"]})
                else:  # Single assignment
                    # Create a final assignment from the return value to the original variable
                    final_assignment = {"type": "execution_assignment", "result": original_results[0], "function": "identity", "args": [return_values[0]], "line": call_node["line"]}
                    self.ir_steps.append(final_assignment)
            else:
                # This is a regular `let` statement inside the UDF.
                # It gets mangled and added directly to the IR.
                self.ir_steps.append(mangled_stmt)

    def _mangle_node(self, node: Any, prefix: str, param_map: Dict[str, Token]) -> Any:
        """Recursively replaces local variable names with mangled versions."""
        if isinstance(node, Token):
            if node.value in param_map:
                return param_map[node.value]
            return Token(node.type, f"{prefix}{node.value}")

        if isinstance(node, dict):
            new_node = node.copy()
            for key, value in node.items():
                if key in ("result", "results"):
                    new_node[key] = [f"{prefix}{v}" for v in value] if isinstance(value, list) else f"{prefix}{value}"
                else:
                    new_node[key] = self._mangle_node(value, prefix, param_map)
            return new_node

        if isinstance(node, list):
            return [self._mangle_node(item, prefix, param_map) for item in node]

        return node


def generate_ir(model: FileSemanticModel) -> List[Dict[str, Any]]:
    """
    High-level entry point for the IR generation stage.
    """
    generator = IRGenerator(model)
    return generator.generate()
