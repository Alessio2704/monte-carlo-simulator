from typing import List, Dict, Any


class IdentityEliminator:
    """
    Performs the Identity Elimination optimization phase.

    This pass simplifies the IR by removing redundant 'identity' function
    calls that wrap a nested expression. This pattern is commonly generated
    by the IR generator for UDF return statements.

    For example, it transforms this:
    {
      "type": "execution_assignment",
      "result": ["z"],
      "function": "identity",
      "args": [{"function": "add", "args": ["x", 5]}]
    }

    Into this:
    {
      "type": "execution_assignment",
      "result": ["z"],
      "function": "add",
      "args": ["x", 5]
    }
    """

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Iterates through the IR and rebuilds it, applying the simplification
        rule where applicable.
        """
        optimized_ir: List[Dict[str, Any]] = []

        for step in ir:
            # Check if the step is a candidate for this optimization
            is_identity_call = step.get("function") == "identity"
            has_one_arg = len(step.get("args", [])) == 1

            if is_identity_call and has_one_arg:
                inner_arg = step["args"][0]
                is_nested_expression = isinstance(inner_arg, dict) and "function" in inner_arg

                if is_nested_expression:
                    # Rewrite the step by lifting the inner expression
                    new_step = {
                        "type": "execution_assignment",
                        "result": step["result"],
                        "function": inner_arg["function"],
                        "args": inner_arg.get("args", []),
                        "line": step.get("line", -1),
                    }
                    optimized_ir.append(new_step)
                    continue  # Skip appending the original step

            # If the rule doesn't apply, keep the original step
            optimized_ir.append(step)

        return optimized_ir


def run_identity_elimination(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the identity elimination optimization phase."""
    optimizer = IdentityEliminator()
    return optimizer.optimize(ir)
