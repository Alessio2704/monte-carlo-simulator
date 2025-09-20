from typing import List, Dict, Any, Set

# The model is passed in as a dictionary, not the formal FileSemanticModel class
# from vsc.data_structures import FileSemanticModel


class DeadCodeEliminator:
    """
    Performs the Dead Code Elimination (DCE) optimization phase.

    This pass identifies and removes instructions whose results are not used,
    either directly or indirectly, to compute the final @output variable.
    It works by performing a backwards "liveness" analysis pass, followed by
    a forward filtering pass.
    """

    def __init__(self, ir: List[Dict[str, Any]], model: Dict[str, Any]):
        self.ir = ir
        self.model = model
        # We can reuse the variable finding logic from the validator.
        from .ir_validator import IRValidator

        self._find_used_variables = IRValidator([])._find_used_variables

    def optimize(self) -> List[Dict[str, Any]]:
        """Main entry point for the DCE optimization."""

        main_file_path = self.model.get("main_file_path")
        if not main_file_path:
            return self.ir

        main_ast = self.model.get("processed_asts", {}).get(main_file_path)
        if not main_ast:
            return self.ir

        output_directive_node = next((d for d in main_ast.get("directives", []) if d.get("name") == "output"), None)

        if not output_directive_node:
            return self.ir

        root_variable = output_directive_node["value"]

        live_variables: Set[str] = {root_variable}

        for step in reversed(self.ir):
            result_vars = set(step.get("result", []))

            if not result_vars.isdisjoint(live_variables):
                input_vars = self._find_used_variables(step.copy())
                live_variables.update(input_vars)

        final_ir: List[Dict[str, Any]] = []
        for step in self.ir:
            result_vars = set(step.get("result", []))

            if not result_vars.isdisjoint(live_variables):
                final_ir.append(step)

        return final_ir


def run_dce(ir: List[Dict[str, Any]], model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """High-level entry point for the Dead Code Elimination optimization phase."""
    optimizer = DeadCodeEliminator(ir, model)
    return optimizer.optimize()
