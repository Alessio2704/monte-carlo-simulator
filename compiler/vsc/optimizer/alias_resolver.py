from typing import List, Dict, Any


class AliasResolver:
    """
    Performs a powerful alias resolution optimization. This pass handles all
    forms of simple aliasing created by the IR Generator, including:
    1. Direct aliasing: `let x = identity(__temp_x)`
    2. Expression aliasing: `let x = identity(add(__temp_y, 5))`

    It rewrites the source instruction that produced the temporary variable/expression
    to use the final variable name, and eliminates the redundant identity instruction.
    This is crucial for restoring user-defined variable names and simplifying
    the IR structure before constant folding.
    """

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        optimized_ir = ir[:]

        while True:
            made_change = False
            identity_index_to_remove = -1

            for i, step in enumerate(optimized_ir):
                is_identity = step.get("function") == "identity"
                is_single_assign = len(step.get("result", [])) == 1

                if is_identity and is_single_assign:
                    args = step.get("args", [])
                    if len(args) != 1:
                        continue

                    target_var = step["result"][0]
                    source_node = args[0]

                    # Case 1: The source is a simple variable (e.g., identity(__temp_x))
                    if isinstance(source_node, str):
                        source_var = source_node
                        source_def_index = -1
                        for j in range(i - 1, -1, -1):
                            source_results = optimized_ir[j].get("result", [])
                            if len(source_results) == 1 and source_results[0] == source_var:
                                source_def_index = j
                                break

                        if source_def_index != -1:
                            optimized_ir[source_def_index]["result"] = [target_var]
                            identity_index_to_remove = i
                            made_change = True
                            break

                    # Case 2: The source is a nested expression (e.g., identity(add(...)))
                    elif isinstance(source_node, dict) and "function" in source_node:
                        # This is the former job of IdentityElimination.
                        # We rewrite the identity instruction into the nested expression.
                        optimized_ir[i] = {
                            "type": "execution_assignment",
                            "result": [target_var],
                            "function": source_node["function"],
                            "args": source_node.get("args", []),
                            "line": step.get("line", -1),
                        }
                        # We don't remove a line, just modify it in place.
                        # This counts as a change, so we should loop again.
                        made_change = True
                        # We break to restart the scan, as this change might enable other optimizations.
                        break

            if made_change:
                if identity_index_to_remove != -1:
                    optimized_ir = [s for j, s in enumerate(optimized_ir) if j != identity_index_to_remove]
                continue
            else:
                break

        return optimized_ir


def run_alias_resolver(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the alias resolution optimization phase."""
    optimizer = AliasResolver()
    return optimizer.optimize(ir)
