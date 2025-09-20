from typing import List, Dict, Any


class ConstantFolder:
    """
    Performs the Constant Propagation and Folding optimization phase.

    This pass iterates through the IR, keeping track of variables that hold
    constant literal values. It then uses this information to:
    1.  Propagate these constant values into subsequent expressions.
    2.  Fold (evaluate) expressions where all inputs are constant.
    """

    def __init__(self):
        # Maps variable names to their known literal value. e.g., {"x": 10}
        self.constant_map: Dict[str, Any] = {}

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Main entry point for the optimization pass."""
        optimized_ir: List[Dict[str, Any]] = []
        for step in ir:
            # The main processing logic is now encapsulated in _process_step
            optimized_step = self._process_step(step)
            optimized_ir.append(optimized_step)

        return optimized_ir

    def _process_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single top-level IR instruction. This is the main controller.
        """
        # First, handle literal assignments, as they are the source of constants.
        if step["type"] == "literal_assignment":
            # Ensure we only track single-variable assignments as constants
            if len(step["result"]) == 1:
                var_name = step["result"][0]
                self.constant_map[var_name] = step["value"]
            return step

        # For any other instruction, we create a copy and try to evaluate its parts.
        optimized_step = step.copy()

        # We recursively evaluate only the expression parts of the instruction.
        if "args" in optimized_step:
            optimized_step["args"] = [self._evaluate_expression(arg) for arg in optimized_step["args"]]
        if "condition" in optimized_step:
            optimized_step["condition"] = self._evaluate_expression(optimized_step["condition"])
        if "then_expr" in optimized_step:
            optimized_step["then_expr"] = self._evaluate_expression(optimized_step["then_expr"])
        if "else_expr" in optimized_step:
            optimized_step["else_expr"] = self._evaluate_expression(optimized_step["else_expr"])

        # Now, try to fold the entire instruction based on the evaluated parts.
        folded_result = self._fold_instruction(optimized_step)

        # If folding produced a single literal value, we rewrite the instruction.
        if not isinstance(folded_result, dict):
            return {
                "type": "literal_assignment",
                "result": step["result"],
                "value": folded_result,
                "line": step.get("line", -1),
            }

        # Otherwise, return the instruction with its parts (potentially) simplified.
        return folded_result

    def _evaluate_expression(self, node: Any) -> Any:
        """
        Recursively evaluates a pure expression node, propagating constants and
        folding where possible. Returns a literal or a simplified expression dict.
        """
        # Base case 1: It's a variable name. Propagate its constant value if known.
        if isinstance(node, str) and node in self.constant_map:
            return self.constant_map[node]

        # Base case 2: It's already a literal or a variable we can't propagate.
        if not isinstance(node, dict):
            return node

        # Recursive step: It's a sub-expression. Evaluate its parts first.
        optimized_node = node.copy()
        if "args" in optimized_node:
            optimized_node["args"] = [self._evaluate_expression(arg) for arg in optimized_node["args"]]
        # (Add condition/then/else here if you support nested conditionals in the future)

        # After evaluating children, try to fold the sub-expression itself.
        return self._fold_instruction(optimized_node)

    def _fold_instruction(self, node: Dict[str, Any]) -> Any:
        """
        Takes an instruction or sub-expression whose children have already been
        evaluated and tries to compute a final literal value.
        """
        # --- Folding for conditionals ---
        node_type = node.get("type")
        if node_type in ("conditional_assignment", "conditional_expression"):
            condition = node["condition"]
            if isinstance(condition, bool):
                # The condition is a known constant, so we can eliminate a branch.
                return node["then_expr"] if condition else node["else_expr"]
            return node  # Cannot fold the conditional yet.

        # --- Folding for function calls ---
        func = node.get("function")
        if not func:
            return node  # Not a foldable function call.

        args = node.get("args", [])
        # We can only fold if ALL arguments are literals.
        if not all(isinstance(arg, (int, float, bool)) for arg in args):
            return node

        # Attempt to compute the result at compile time.
        try:
            if func == "add":
                return args[0] + args[1]
            if func == "subtract":
                return args[0] - args[1]
            if func == "multiply":
                return args[0] * args[1]
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
            if func == "__and__":
                return all(args)
            if func == "__or__":
                return any(args)
            if func == "__not__":
                return not args[0]
        except (TypeError, IndexError):
            # A type error here means something like `5 + "a"`. The semantic
            # validator should have caught it, but we'll be safe and not fold.
            return node

        # If we don't know how to fold this specific function (e.g., "Normal"),
        # we return the node with its (potentially optimized) arguments.
        return node


def run_constant_folding(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the constant folding optimization phase."""
    optimizer = ConstantFolder()
    return optimizer.optimize(ir)
