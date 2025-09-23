import re
from typing import Dict, Any, List, Set
from ..parser import _StringLiteral


class ResourceAllocator:
    """
    Implements Phase 8b of the bytecode pipeline.

    Scans the entire lowered and partitioned IR to create partitioned, typed
    registries for all variables and constants.
    """

    def __init__(self, partitioned_ir: Dict[str, List[Dict[str, Any]]], model: Dict[str, Any]):
        self.full_ir = partitioned_ir.get("pre_trial_steps", []) + partitioned_ir.get("per_trial_steps", [])
        self.model = model
        self.variable_registries: Dict[str, List[str]] = {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []}
        self.variable_map: Dict[str, Dict] = {}
        self.constant_pools: Dict[str, List] = {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []}
        self.constant_map: Dict[str, Dict] = {}

    def allocate(self) -> Dict[str, Any]:
        """Runs the full resource allocation process."""
        self._allocate_constants()
        self._allocate_variables()
        return {"variable_registries": self.variable_registries, "variable_map": self.variable_map, "constant_pools": self.constant_pools, "constant_map": self.constant_map}

    def _is_constant_node(self, node: Any) -> bool:
        if isinstance(node, (int, float, bool, _StringLiteral)):
            return True
        if isinstance(node, str):
            return False  # A raw string is a variable name
        if isinstance(node, dict):
            return False
        if isinstance(node, list):
            return all(self._is_constant_node(item) for item in node)
        return False

    def _get_canonical_key(self, literal: Any) -> str:
        if isinstance(literal, (int, float)):
            return f"s_{float(literal)}"
        if isinstance(literal, bool):
            return f"b_{str(literal).lower()}"
        if isinstance(literal, (_StringLiteral, str)):
            val = literal.value if isinstance(literal, _StringLiteral) else literal
            return f"str_{val}"
        if isinstance(literal, list):
            return f"v_{'_'.join([self._get_canonical_key(item) for item in literal])}"
        return ""

    def _find_literals_in_expression(self, node: Any):
        if isinstance(node, (int, float)):
            key = self._get_canonical_key(node)
            if key not in self.constant_map:
                pool = self.constant_pools["SCALAR"]
                self.constant_map[key] = {"type": "SCALAR", "index": len(pool)}
                pool.append(float(node))
            return

        if isinstance(node, bool):
            key = self._get_canonical_key(node)
            if key not in self.constant_map:
                pool = self.constant_pools["BOOLEAN"]
                self.constant_map[key] = {"type": "BOOLEAN", "index": len(pool)}
                pool.append(node)
            return

        if isinstance(node, _StringLiteral):
            key = self._get_canonical_key(node.value)
            if key not in self.constant_map:
                pool = self.constant_pools["STRING"]
                self.constant_map[key] = {"type": "STRING", "index": len(pool)}
                pool.append(node.value)
            return

        if isinstance(node, list):
            if self._is_constant_node(node):
                key = self._get_canonical_key(node)
                if key not in self.constant_map:
                    pool = self.constant_pools["VECTOR"]
                    self.constant_map[key] = {"type": "VECTOR", "index": len(pool)}
                    # Ensure we unwrap any _StringLiteral objects before adding to the final pool
                    unwrapped_list = [item.value if isinstance(item, _StringLiteral) else item for item in node]
                    pool.append(unwrapped_list)
                    return

            for item in node:
                self._find_literals_in_expression(item)
            return

        if isinstance(node, dict):
            if node.get("function") == "identity":
                return

            for arg in node.get("args", []):
                self._find_literals_in_expression(arg)
            for key in ["condition", "then_expr", "else_expr", "value"]:
                if key in node:
                    self._find_literals_in_expression(node[key])
            return

    def _allocate_constants(self):
        """Unified constant allocation by scanning every part of every instruction."""
        for step in self.full_ir:
            self._find_literals_in_expression(step)

    def _get_variable_type_from_model(self, var_name: str) -> str:
        # Check global variables first, which now includes temp variables from the lowerer
        if var_name in self.model["global_variables"]:
            return self.model["global_variables"][var_name]["inferred_type"]

        # Check for mangled UDF variables as a fallback
        mangled_match = re.match(r"^__(.+)_[0-9]+__(.+)$", var_name)
        if mangled_match:
            original_func_name, original_var_name = mangled_match.groups()
            if original_func_name in self.model["user_defined_functions"]:
                func_scope = self.model["user_defined_functions"][original_func_name]
                if original_var_name in func_scope["discovered_body"]:
                    return func_scope["discovered_body"][original_var_name]["inferred_type"]

        # Fallback for older temporary variables from the IR generator (pre-lifting)
        if var_name.startswith("__temp_"):
            return "scalar"

        raise NameError(f"Internal Compiler Error: Could not find type for variable '{var_name}' in model.")

    def _allocate_variables(self):
        all_var_names: Set[str] = set()
        for step in self.full_ir:
            all_var_names.update(step.get("result", []))

        typed_vars: Dict[str, List[str]] = {"SCALAR": [], "VECTOR": [], "BOOLEAN": [], "STRING": []}

        for var_name in sorted(list(all_var_names)):
            if var_name in self.variable_map:
                continue
            var_type_str = self._get_variable_type_from_model(var_name)
            registry_type = var_type_str.upper()
            if isinstance(registry_type, list):
                continue
            typed_vars[registry_type].append(var_name)

        for reg_type, var_list in typed_vars.items():
            for var_name in sorted(var_list):
                registry = self.variable_registries[reg_type]
                index = len(registry)
                registry.append(var_name)
                self.variable_map[var_name] = {"type": reg_type, "index": index}
