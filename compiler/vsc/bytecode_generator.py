from typing import List, Dict, Any
from lark import Token

from .parser import _StringLiteral
from .exceptions import ValuaScriptError, ErrorCode


class BytecodeGenerator:
    """
    Generates the final JSON recipe (bytecode) from the partitioned IR.
    It builds the variable registry, resolves all variable names to integer
    indices, and structures the final output for the simulation engine.
    """

    def __init__(self, partitioned_ir: Dict[str, List[Dict[str, Any]]], model: Dict[str, Any]):
        self.partitioned_ir = partitioned_ir
        self.model = model
        self.variable_registry: List[str] = []
        self.name_to_index_map: Dict[str, int] = {}

    def generate(self) -> Dict[str, Any]:
        """Generates the complete JSON recipe."""
        self._build_variable_registry()

        sim_config = self._get_simulation_config()
        output_var_index = self._get_output_variable_index()

        pre_trial_bytecode = self._rewrite_steps(self.partitioned_ir["pre_trial_steps"])
        per_trial_bytecode = self._rewrite_steps(self.partitioned_ir["per_trial_steps"])

        return {
            "simulation_config": sim_config,
            "variable_registry": self.variable_registry,
            "output_variable_index": output_var_index,
            "pre_trial_steps": pre_trial_bytecode,
            "per_trial_steps": per_trial_bytecode,
        }

    def _build_variable_registry(self):
        all_vars = set()
        # Collect variables from both partitions
        all_steps = self.partitioned_ir["pre_trial_steps"] + self.partitioned_ir["per_trial_steps"]
        for step in all_steps:
            # Handle both single ('result') and multiple ('results') assignment keys
            results = step.get("results") or step.get("result", [])
            # Ensure results is always a list for uniform processing
            if isinstance(results, str):
                results = [results]
            all_vars.update(results)

        # Sort for deterministic output
        self.variable_registry = sorted(list(all_vars))
        self.name_to_index_map = {name: i for i, name in enumerate(self.variable_registry)}

    def _get_simulation_config(self) -> Dict[str, Any]:
        config = {}
        # The model structure is a dictionary, so access items with .get()
        iterations_directive = self.model.get("directives", {}).get("iterations")
        if iterations_directive:
            config["num_trials"] = iterations_directive["value"]

        output_file_directive = self.model.get("directives", {}).get("output_file")
        if output_file_directive:
            config["output_file"] = output_file_directive["value"]  # Value is already unwrapped

        return config

    def _get_output_variable_index(self) -> int:
        output_directive = self.model.get("directives", {}).get("output")
        if not output_directive:
            raise ValuaScriptError(ErrorCode.MISSING_OUTPUT_DIRECTIVE)

        output_var_name = output_directive["value"]
        if output_var_name not in self.name_to_index_map:
            raise ValuaScriptError(
                ErrorCode.UNDEFINED_VARIABLE,
                name=output_var_name,
                message=f"The final @output variable '{output_var_name}' was not found. It may have been eliminated as dead code if optimizations are enabled.",
            )

        return self.name_to_index_map[output_var_name]

    def _rewrite_steps(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        bytecode = []
        for step in steps:
            # Handle both single ('result') and multiple ('results') assignment keys
            results = step.get("results") or step.get("result", [])
            if isinstance(results, str):
                results = [results]

            result_indices = [self.name_to_index_map[r] for r in results]

            new_step = {
                "type": step.get("type", "execution_assignment"),  # Keep original type
                "result": result_indices,
                "line": step.get("line", -1),
            }

            # Add other keys if they exist, resolving arguments
            if "function" in step:
                new_step["function"] = step["function"]
                new_step["args"] = [self._resolve_arg(arg) for arg in step.get("args", [])]
            if "value" in step:
                new_step["value"] = self._resolve_arg(step["value"])
            if "condition" in step:
                new_step["condition"] = self._resolve_arg(step["condition"])
                new_step["then_expr"] = self._resolve_arg(step["then_expr"])
                new_step["else_expr"] = self._resolve_arg(step["else_expr"])

            bytecode.append(new_step)
        return bytecode

    def _resolve_arg(self, arg: Any) -> Any:
        """Recursively converts an IR argument into its final bytecode format."""
        if isinstance(arg, str):  # After optimization, variable refs are strings
            return {"type": "variable_index", "value": self.name_to_index_map[arg]}
        if isinstance(arg, bool):
            return {"type": "boolean_literal", "value": arg}
        if isinstance(arg, (int, float)):
            return {"type": "scalar_literal", "value": arg}
        if isinstance(arg, _StringLiteral):  # Check if this class still exists at this stage
            return {"type": "string_literal", "value": arg.value}
        if isinstance(arg, list):
            # Recurse for items inside the list
            return {"type": "vector_literal", "value": [self._resolve_arg(item) for item in arg]}

        if isinstance(arg, dict):
            # This handles nested expressions
            new_dict = arg.copy()
            if "args" in new_dict:
                new_dict["args"] = [self._resolve_arg(a) for a in new_dict.get("args", [])]
            return new_dict

        # Fallback for unexpected types
        return arg


def generate_bytecode(partitioned_ir: Dict[str, List[Dict[str, Any]]], model: Dict[str, Any]) -> Dict[str, Any]:
    """High-level entry point for the bytecode generation stage."""
    generator = BytecodeGenerator(partitioned_ir, model)
    return generator.generate()
