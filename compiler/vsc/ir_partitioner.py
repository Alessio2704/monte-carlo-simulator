from typing import List, Dict, Any, Set
from .functions import FUNCTION_SIGNATURES


class IRPartitioner:
    """
    Performs Stage 7 of compilation: partitioning the linear IR into two
    blocks: 'pre_trial_steps' for deterministic calculations and
    'per_trial_steps' for stochastic calculations. This is done using a robust,
    multi-pass tainting algorithm to correctly handle dependency chains.
    """

    def __init__(self, optimized_ir: List[Dict[str, Any]], model: Dict[str, Any]):
        self.ir = optimized_ir
        self.model = model
        self.stochastic_functions = {name for name, sig in FUNCTION_SIGNATURES.items() if sig.get("is_stochastic", False)}
        from .optimizer.ir_validator import IRValidator

        self._find_used_variables = IRValidator([])._find_used_variables

    def partition(self) -> Dict[str, List[Dict[str, Any]]]:
        """Executes the partitioning process."""
        stochastic_vars = self._run_tainting_pass()

        pre_trial_steps: List[Dict[str, Any]] = []
        per_trial_steps: List[Dict[str, Any]] = []

        for step in self.ir:
            output_vars = set(step.get("result", []))
            if not output_vars.isdisjoint(stochastic_vars):
                per_trial_steps.append(step)
            else:
                pre_trial_steps.append(step)

        return {
            "pre_trial_steps": pre_trial_steps,
            "per_trial_steps": per_trial_steps,
        }

    def _step_contains_stochastic_func(self, node: Any) -> bool:
        """
        Recursively searches a node (dict, list, etc.) to see if it contains
        a call to any known stochastic function.
        """
        if isinstance(node, dict):
            if node.get("function") in self.stochastic_functions:
                return True
            for value in node.values():
                if self._step_contains_stochastic_func(value):
                    return True
        elif isinstance(node, list):
            for item in node:
                if self._step_contains_stochastic_func(item):
                    return True
        return False

    def _run_tainting_pass(self) -> Set[str]:
        """
        Performs a fixed-point iteration over the IR to find all variables that
        are directly or indirectly dependent on a stochastic source.
        """
        stochastic_vars: Set[str] = set()

        for step in self.ir:
            if self._step_contains_stochastic_func(step):
                stochastic_vars.update(step.get("result", []))

        while True:
            newly_tainted_count = 0
            for step in self.ir:
                output_vars = set(step.get("result", []))
                if output_vars.issubset(stochastic_vars):
                    continue

                input_vars = self._find_used_variables(step)

                if not input_vars.isdisjoint(stochastic_vars):
                    new_vars = output_vars - stochastic_vars
                    if new_vars:
                        stochastic_vars.update(new_vars)
                        newly_tainted_count += len(new_vars)

            if newly_tainted_count == 0:
                break

        return stochastic_vars


def partition_ir(optimized_ir: List[Dict[str, Any]], model: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """High-level entry point for the IR partitioning stage."""
    partitioner = IRPartitioner(optimized_ir, model)
    return partitioner.partition()
