from typing import List, Dict, Any
import copy
from ..functions import FUNCTION_SIGNATURES


class ConstantFolder:
    """
    Performs the Constant Propagation and Folding optimization phase.
    This pass iterates through the IR until a fixed point is reached, ensuring
    that all possible constant expressions are evaluated. It uses a data-driven
    approach, executing `const_folder` lambdas defined in function signatures.
    """

    def __init__(self):
        self.signatures = FUNCTION_SIGNATURES
        self.constant_map: Dict[str, Any] = {}

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Main entry point for the optimization pass."""
        current_ir = ir
        while True:
            ir_before_pass = copy.deepcopy(current_ir)
            self.constant_map = {}

            optimized_ir: List[Dict[str, Any]] = []
            for step in current_ir:
                optimized_step = self._process_step(step)
                optimized_ir.append(optimized_step)

            current_ir = optimized_ir

            if current_ir == ir_before_pass:
                break

        return current_ir

    def _process_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single top-level IR instruction.
        """
        if "result" not in step:
            return step

        if step["type"] == "literal_assignment":
            if len(step["result"]) == 1:
                var_name = step["result"][0]
                self.constant_map[var_name] = step["value"]
            return step

        optimized_step = step.copy()

        if "args" in optimized_step:
            optimized_step["args"] = [self._evaluate_expression(arg) for arg in optimized_step["args"]]
        if "condition" in optimized_step:
            optimized_step["condition"] = self._evaluate_expression(optimized_step["condition"])
        if "then_expr" in optimized_step:
            optimized_step["then_expr"] = self._evaluate_expression(optimized_step["then_expr"])
        if "else_expr" in optimized_step:
            optimized_step["else_expr"] = self._evaluate_expression(optimized_step["else_expr"])

        folded_result = self._fold_instruction(optimized_step)

        # Case 1: The instruction was fully folded into a simple literal value.
        # Rewrite the entire step as a literal_assignment.
        if not isinstance(folded_result, dict):
            rewritten_step = {
                "type": "literal_assignment",
                "result": step["result"],
                "value": folded_result,
                "line": step.get("line", -1),
            }
            if len(rewritten_step["result"]) == 1:
                var_name = rewritten_step["result"][0]
                self.constant_map[var_name] = rewritten_step["value"]
            return rewritten_step

        # Case 2: The result is still an expression-like dictionary.
        # We must rebuild the original assignment instruction, preserving the result key.

        # Subcase 2a: The result is a simple function call (e.g., from a chosen conditional branch).
        if "function" in folded_result and "type" not in folded_result:
            return {
                "type": "execution_assignment",
                "result": step["result"],
                "function": folded_result["function"],
                "args": folded_result.get("args", []),
                "line": step.get("line", -1),
            }

        # Subcase 2b: The result is a complex expression, like a conditional_expression
        # that was returned from a partially-folded conditional_assignment.
        if "type" in folded_result and folded_result["type"] == "conditional_expression":
            return {
                "type": "conditional_assignment",
                "result": step["result"],
                "condition": folded_result["condition"],
                "then_expr": folded_result["then_expr"],
                "else_expr": folded_result["else_expr"],
                "line": step.get("line", -1),
            }

        # Case 3: The instruction was only partially optimized, but its overall structure
        # (e.g. execution_assignment) did not change. Return the modified version.
        return folded_result

    def _evaluate_expression(self, node: Any) -> Any:
        if isinstance(node, str) and node in self.constant_map:
            return self.constant_map[node]
        if not isinstance(node, dict):
            return node

        optimized_node = node.copy()
        if "args" in optimized_node:
            optimized_node["args"] = [self._evaluate_expression(arg) for arg in optimized_node["args"]]
        return self._fold_instruction(optimized_node)

    def _fold_instruction(self, node: Dict[str, Any]) -> Any:
        node_type = node.get("type")
        if node_type in ("conditional_assignment", "conditional_expression"):
            condition = node["condition"]
            if isinstance(condition, bool):
                return node["then_expr"] if condition else node["else_expr"]
            return node
        func_name = node.get("function")
        if not func_name:
            return node

        args = node.get("args", [])
        if not all(isinstance(arg, (int, float, bool, list)) for arg in args):
            return node  # Cannot fold if it contains unresolved variables

        sig = self.signatures.get(func_name)
        if not sig or not sig.get("const_folder"):
            return node

        folder_lambda = sig["const_folder"]
        try:
            result = folder_lambda(args)
            if result is not None:
                return result
        except (ValueError, TypeError, IndexError, ZeroDivisionError):
            return node
        return node


def run_constant_folding(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the constant folding optimization phase."""
    optimizer = ConstantFolder()
    return optimizer.optimize(ir)
