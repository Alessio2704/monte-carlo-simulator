from typing import List, Dict, Any
import copy


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
        2. Fully resolve chained identities within the map.
        3. Create a new IR with the variables substituted and identities removed.
        """
        # Pass 1: Build the initial replacement map from temporary identities
        for i, step in enumerate(ir):
            if step.get("function") == "identity" and step["result"][0].startswith("__"):
                variable_to_replace = step["result"][0]
                replacement_value = step["args"][0]
                self.replacement_map[variable_to_replace] = replacement_value
                self.identity_indices_to_remove.add(i)

        if not self.replacement_map:
            return ir

        # Pass 2: Fully resolve chained replacements in the map
        self._resolve_replacement_map()

        # Pass 3: Build the new IR with substitutions
        optimized_ir: List[Dict[str, Any]] = []
        for i, step in enumerate(ir):
            if i in self.identity_indices_to_remove:
                continue

            new_step = copy.deepcopy(step)
            self._substitute_in_node(new_step)
            optimized_ir.append(new_step)

        return optimized_ir

    def _resolve_replacement_map(self):
        """
        Iteratively resolves the replacement map until all values are final.
        """
        changed = True
        while changed:
            changed = False
            for var_to_replace, replacement_val in self.replacement_map.items():
                if isinstance(replacement_val, str) and replacement_val in self.replacement_map:
                    new_replacement = self.replacement_map[replacement_val]
                    if new_replacement != replacement_val:
                        self.replacement_map[var_to_replace] = new_replacement
                        changed = True

    def _substitute_in_node(self, node: Any):
        """
        Recursively traverses the IR and replaces variables found in the replacement map.
        """
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "args" and isinstance(value, list):
                    for i, arg in enumerate(value):
                        if isinstance(arg, str) and arg in self.replacement_map:
                            node["args"][i] = self.replacement_map[arg]
                        else:
                            self._substitute_in_node(arg)
                else:
                    self._substitute_in_node(value)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                if isinstance(item, str) and item in self.replacement_map:
                    node[i] = self.replacement_map[item]
                else:
                    self._substitute_in_node(item)


def run_copy_propagation(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the copy propagation optimization phase."""
    optimizer = CopyPropagator()
    return optimizer.optimize(ir)
