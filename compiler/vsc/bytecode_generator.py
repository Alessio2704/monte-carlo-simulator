from typing import List, Dict, Any
from lark import Token

from .data_structures import FileSemanticModel
from .parser import _StringLiteral
from .exceptions import ValuaScriptError


class BytecodeGenerator:
    """
    Generates the final JSON recipe (bytecode) from the optimized IR.
    It builds the variable registry, resolves all variable names to integer
    indices, and structures the final output for the simulation engine.
    """

    def __init__(self, optimized_ir: Dict[str, List[Dict[str, Any]]], model: FileSemanticModel):
        self.optimized_ir = optimized_ir
        self.model = model
        self.variable_registry: List[str] = []
        self.name_to_index_map: Dict[str, int] = {}

    def generate(self) -> Dict[str, Any]:
        """Generates the complete JSON recipe."""
        self._build_variable_registry()

        sim_config = self._get_simulation_config()
        output_var_index = self._get_output_variable_index()

        pre_trial_bytecode = self._rewrite_steps(self.optimized_ir["pre_trial_steps"])
        per_trial_bytecode = self._rewrite_steps(self.optimized_ir["per_trial_steps"])

        return {
            "simulation_config": sim_config,
            "variable_registry": self.variable_registry,
            "output_variable_index": output_var_index,
            "pre_trial_steps": pre_trial_bytecode,
            "per_trial_steps": per_trial_bytecode,
        }

    def _build_variable_registry(self):
        all_vars = set()
        all_steps = self.optimized_ir["pre_trial_steps"] + self.optimized_ir["per_trial_steps"]
        for step in all_steps:
            results = step.get("results") or [step.get("result")]
            all_vars.update(results)

        self.variable_registry = sorted(list(all_vars))
        self.name_to_index_map = {name: i for i, name in enumerate(self.variable_registry)}

    def _get_simulation_config(self) -> Dict[str, Any]:
        config = {}
        iterations_directive = self.model.directives.get("iterations")
        if iterations_directive:
            config["num_trials"] = iterations_directive["value"]

        output_file_directive = self.model.directives.get("output_file")
        if output_file_directive:
            config["output_file"] = output_file_directive["value"].value

        return config

    def _get_output_variable_index(self) -> int:
        output_directive = self.model.directives.get("output")
        if not output_directive:
            raise ValuaScriptError(ErrorCode.MISSING_OUTPUT_DIRECTIVE)

        output_var_name = output_directive["value"].value
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
            results = step.get("results") or [step.get("result")]
            result_indices = [self.name_to_index_map[r] for r in results]

            new_step = {
                "type": "execution_assignment",
                "result": result_indices,
                "line": step.get("line", -1),
                "function": step.get("function"),
                "args": [self._resolve_arg(arg) for arg in step.get("args", [])],
            }
            bytecode.append(new_step)
        return bytecode

    def _resolve_arg(self, arg: Any) -> Dict[str, Any]:
        """Recursively converts an IR argument into its final bytecode format."""
        if isinstance(arg, Token):
            return {"type": "variable_index", "value": self.name_to_index_map[arg.value]}
        if isinstance(arg, bool):
            return {"type": "boolean_literal", "value": arg}
        if isinstance(arg, (int, float)):
            return {"type": "scalar_literal", "value": arg}
        if isinstance(arg, _StringLiteral):
            return {"type": "string_literal", "value": arg.value}
        if isinstance(arg, list):
            return {"type": "vector_literal", "value": arg}

        if isinstance(arg, dict):
            # This handles nested expressions, which after IR generation are always built-ins
            return {
                "type": "execution_assignment",
                "function": arg["function"],
                "args": [self._resolve_arg(a) for a in arg.get("args", [])],
            }

        raise TypeError(f"Internal Error: Unhandled type '{type(arg).__name__}' during bytecode generation.")


def generate_bytecode(optimized_ir: Dict[str, List[Dict[str, Any]]], model: FileSemanticModel) -> Dict[str, Any]:
    """High-level entry point for the bytecode generation stage."""
    generator = BytecodeGenerator(optimized_ir, model)
    return generator.generate()
