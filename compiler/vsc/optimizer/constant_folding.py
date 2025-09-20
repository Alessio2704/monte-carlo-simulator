from typing import List, Dict, Any
import math
import copy


class ConstantFolder:
    """
    Performs the Constant Propagation and Folding optimization phase.
    This pass iterates through the IR until a fixed point is reached, ensuring
    that all possible constant expressions are evaluated.
    """

    def __init__(self):
        self.constant_map: Dict[str, Any] = {}

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Main entry point for the optimization pass."""

        current_ir = ir
        while True:
            # Create a deep copy to compare against after the pass
            ir_before_pass = copy.deepcopy(current_ir)
            self.constant_map = {}  # Reset map for each full pass

            optimized_ir: List[Dict[str, Any]] = []
            for step in current_ir:
                optimized_step = self._process_step(step)
                optimized_ir.append(optimized_step)

            current_ir = optimized_ir

            # If the IR has not changed after a full pass, we've reached a fixed point.
            if current_ir == ir_before_pass:
                break

        return current_ir

    def _process_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
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
        func = node.get("function")
        if not func:
            return node
        args = node.get("args", [])
        if not all(isinstance(arg, (int, float, bool)) for arg in args):
            return node
        try:
            if func in ("add", "multiply", "__and__", "__or__"):
                if func == "add":
                    return sum(args)
                if func == "multiply":
                    return math.prod(args)
                if func == "__and__":
                    return all(args)
                if func == "__or__":
                    return any(args)
            if func in ("log", "log10", "exp", "sin", "cos", "tan", "__not__"):
                if len(args) != 1:
                    return node
                if func == "log":
                    return math.log(args[0]) if args[0] > 0 else node
                if func == "log10":
                    return math.log10(args[0]) if args[0] > 0 else node
                if func == "exp":
                    return math.exp(args[0])
                if func == "sin":
                    return math.sin(args[0])
                if func == "cos":
                    return math.cos(args[0])
                if func == "tan":
                    return math.tan(args[0])
                if func == "__not__":
                    return not args[0]
            if len(args) != 2:
                return node
            if func == "subtract":
                return args[0] - args[1]
            if func == "divide":
                return args[0] / args[1] if args[1] != 0 else node
            if func == "power":
                return args[0] ** args[1]
            if func == "__gt__":
                return args[0] > args[1]
            if func == "__lt__":
                return args[0] < args[1]
            if func == "__gte__":
                return args[0] >= args[1]
            if func == "__lte__":
                return args[0] <= args[1]
            if func == "__eq__":
                return args[0] == args[1]
            if func == "__neq__":
                return args[0] != args[1]
        except (TypeError, IndexError, ValueError):
            return node
        return node


def run_constant_folding(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the constant folding optimization phase."""
    optimizer = ConstantFolder()
    return optimizer.optimize(ir)
