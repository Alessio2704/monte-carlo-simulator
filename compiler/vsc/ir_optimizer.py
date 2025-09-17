from typing import List, Dict, Any, Set, Tuple
from collections import deque
from lark import Token

from .data_structures import FileSemanticModel
from .functions import FUNCTION_SIGNATURES


class IROptimizer:
    """
    Applies optimizations to the linear Intermediate Representation.
    - Dead Code Elimination (DCE): Removes unused variables and calculations.
    - Loop-Invariant Code Motion (LICM): Separates deterministic (pre-trial)
      and stochastic (per-trial) execution steps.
    """

    def __init__(self, ir: List[Dict[str, Any]], model: FileSemanticModel, dce_enabled: bool):
        self.ir = ir
        self.model = model
        self.dce_enabled = dce_enabled
        self.dependencies: Dict[str, Set[str]] = {}
        self.dependents: Dict[str, Set[str]] = {}

    def optimize(self) -> Dict[str, List[Dict[str, Any]]]:
        """Runs the full optimization pipeline."""

        # Dead Code Elimination must run first
        if self.dce_enabled:
            self._run_dce()

        self._build_dependency_graphs()

        stochastic_vars = self._find_stochastic_variables()

        pre_trial_steps = []
        per_trial_steps = []

        for step in self.ir:
            results = step.get("results") or [step.get("result")]
            # A step is stochastic if any of its output variables are stochastic
            if any(res in stochastic_vars for res in results):
                per_trial_steps.append(step)
            else:
                pre_trial_steps.append(step)

        # Note: Topological sort is implicitly handled by the IR generation order.
        return {
            "pre_trial_steps": pre_trial_steps,
            "per_trial_steps": per_trial_steps,
        }

    def _run_dce(self):
        """Removes all steps that do not contribute to the final @output variable."""
        output_var_directive = self.model.directives.get("output")
        if not output_var_directive:
            # Cannot perform DCE without a designated output
            return

        # The value of an @output directive is a Token
        output_var_name = output_var_directive["value"].value

        self._build_dependency_graphs()

        live_variables = set()
        queue = deque([output_var_name])

        while queue:
            current_var = queue.popleft()
            if current_var not in live_variables:
                live_variables.add(current_var)
                for dep in self.dependencies.get(current_var, set()):
                    queue.append(dep)

        # Filter the IR, keeping only steps where at least one result is "live"
        live_ir = []
        for step in self.ir:
            results = step.get("results") or [step.get("result")]
            if any(res in live_variables for res in results):
                live_ir.append(step)

        self.ir = live_ir

    def _build_dependency_graphs(self):
        """Builds forward and reverse dependency graphs from the IR."""
        self.dependencies.clear()
        self.dependents.clear()

        all_vars = set()
        for step in self.ir:
            results = step.get("results") or [step.get("result")]
            all_vars.update(results)

        for var in all_vars:
            self.dependents[var] = set()

        for step in self.ir:
            results = step.get("results") or [step.get("result")]
            step_deps = self._get_deps_from_node(step)
            for res in results:
                self.dependencies[res] = step_deps

            for dep in step_deps:
                if dep in self.dependents:
                    self.dependents[dep].add(res)

    def _get_deps_from_node(self, node: Any) -> Set[str]:
        """Recursively extracts all variable dependencies from an IR node."""
        deps = set()
        if isinstance(node, Token):
            deps.add(node.value)
        elif isinstance(node, dict):
            for value in node.values():
                deps.update(self._get_deps_from_node(value))
        elif isinstance(node, list):
            for item in node:
                deps.update(self._get_deps_from_node(item))
        return deps

    def _find_stochastic_variables(self) -> Set[str]:
        """
        Finds all stochastic variables by finding stochastic sources
        and then propagating the "taint" to all dependent variables.
        """
        stochastic_sources = set()
        for step in self.ir:
            func_name = step.get("function")
            if func_name and FUNCTION_SIGNATURES.get(func_name, {}).get("is_stochastic"):
                results = step.get("results") or [step.get("result")]
                stochastic_sources.update(results)

        stochastic_vars = set()
        queue = deque(list(stochastic_sources))
        while queue:
            current_var = queue.popleft()
            if current_var not in stochastic_vars:
                stochastic_vars.add(current_var)
                for dependent in self.dependents.get(current_var, set()):
                    queue.append(dependent)

        return stochastic_vars


def optimize_ir(ir: List[Dict[str, Any]], model: FileSemanticModel, dce_enabled: bool) -> Dict[str, List[Dict[str, Any]]]:
    """High-level entry point for the IR optimization stage."""
    optimizer = IROptimizer(ir, model, dce_enabled)
    return optimizer.optimize()
