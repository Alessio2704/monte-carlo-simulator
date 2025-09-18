from typing import List, Dict, Any

class CopyPropagator:
    """
    Performs the Copy Propagation optimization phase.

    This pass finds all temporary identity assignments created for UDF parameter
    passing (e.g., `let __p = identity(y)`). It targets assignments to mangled
    variables that start with '__'.

    It then replaces all subsequent uses of the temporary variable `__p` with the
    original value `y` and removes the now-redundant assignment. This effectively
    "forwards" the parameter value directly into the function's body.
    """

    def __init__(self):
        self.replacement_map: Dict[str, Any] = {}
        self.identity_indices_to_remove: set[int] = set()

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Runs the optimization process.
        1. Find all temporary identity assignments and build the replacement map.
        2. Fully and recursively resolve chained identities within the map itself.
        3. Rebuild the IR, substituting variables and removing redundant steps.
        """
        for i, step in enumerate(ir):
            if step.get("function") == "identity" and step["result"][0].startswith("__"):
                variable_to_replace = step["result"][0]
                replacement_value = step["args"][0]
                self.replacement_map[variable_to_replace] = replacement_value
                self.identity_indices_to_remove.add(i)

        if not self.replacement_map:
            return ir

        # This is now a deep, recursive resolution of the map's values.
        self._resolve_replacement_map()

        optimized_ir: List[Dict[str, Any]] = []
        for i, step in enumerate(ir):
            if i in self.identity_indices_to_remove:
                continue
            
            # Rebuild the step using the fully resolved map.
            new_step = self._substitute_and_rebuild_node(step)
            optimized_ir.append(new_step)

        return optimized_ir

    def _resolve_replacement_map(self):
        """
        Iteratively and recursively resolves the replacement map until no more
        substitutions can be made anywhere inside the map's values.
        """
        changed = True
        while changed:
            changed = False
            for var_to_replace, current_value in self.replacement_map.items():
                # Recursively rebuild the value, substituting any other variables found within it.
                new_value = self._substitute_and_rebuild_node(current_value)
                
                # If the recursive substitution changed the value, update the map
                # and flag that we need to loop again, as this change might
                # enable further resolutions in other values.
                if new_value != current_value:
                    self.replacement_map[var_to_replace] = new_value
                    changed = True

    def _substitute_and_rebuild_node(self, node: Any) -> Any:
        """
        Recursively traverses a node (dict, list, string, etc.) and returns a
        new version with all variables from the replacement map substituted.
        """
        # Base Case 1: The node is a variable that needs to be replaced.
        if isinstance(node, str) and node in self.replacement_map:
            # We must recurse here as well in case the replacement is another chain
            return self._substitute_and_rebuild_node(self.replacement_map[node])

        # Recursive Case (Dictionary): Rebuild the dictionary with transformed values.
        if isinstance(node, dict):
            return {key: self._substitute_and_rebuild_node(value) for key, value in node.items()}

        # Recursive Case (List): Rebuild the list with transformed items.
        if isinstance(node, list):
            return [self._substitute_and_rebuild_node(item) for item in node]

        # Base Case 2: The node is a literal or something else we don't touch.
        return node


def run_copy_propagation(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the copy propagation optimization phase."""
    optimizer = CopyPropagator()
    return optimizer.optimize(ir)