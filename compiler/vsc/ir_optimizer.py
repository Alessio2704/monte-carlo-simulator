from typing import List, Dict, Any
from .data_structures import FileSemanticModel

# Import the renamed phase
from .optimizer.copy_propagation import run_copy_propagation


class IROptimizer:
    """
    Orchestrates the various optimization phases for the Intermediate Representation.
    """

    def __init__(self, ir: List[Dict[str, Any]], model: FileSemanticModel, phases_to_run: List[str]):
        self.ir = ir
        self.model = model
        self.phases_to_run = phases_to_run
        self.artifacts: Dict[str, Any] = {}

    def optimize(self) -> Dict[str, Any]:
        """
        Runs the selected optimization phases in sequence and returns a dictionary
        of all generated artifacts.
        """
        current_ir = self.ir

        # Use the new, clearer name for the phase
        if "copy_propagation" in self.phases_to_run:
            current_ir = run_copy_propagation(current_ir)
            self.artifacts["copy_propagation"] = current_ir

        return self.artifacts


def optimize_ir(ir: List[Dict[str, Any]], model: FileSemanticModel, stop_after_phase: str) -> Dict[str, Any]:
    """
    High-level entry point for the IR optimization stage.
    """
    phases_to_run = []
    # Translate the CLI flag to the internal phase name
    if stop_after_phase == "copy_prop":
        phases_to_run.append("copy_propagation")

    optimizer = IROptimizer(ir, model, phases_to_run)
    return optimizer.optimize()
