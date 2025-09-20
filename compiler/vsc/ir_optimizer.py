from typing import List, Dict, Any
from .data_structures import FileSemanticModel

from .optimizer.copy_propagation import run_copy_propagation
from .optimizer.identity_elimination import run_identity_elimination
from .optimizer.constant_folding import run_constant_folding
from .optimizer.dead_code_elimination import run_dce


class IROptimizer:
    """
    Orchestrates the various optimization phases for the Intermediate Representation.
    """

    def __init__(self, ir: List[Dict[str, Any]], model: FileSemanticModel, phases_to_run: List[str]):
        self.ir = ir
        self.model = model
        self.phase_sequence = ["copy_propagation", "identity_elimination", "constant_folding", "dead_code_elimination"]
        self.phases_to_run = [p for p in self.phase_sequence if p in phases_to_run]
        self.artifacts: Dict[str, Any] = {}

    def optimize(self) -> Dict[str, Any]:
        """
        Runs the selected optimization phases in sequence and returns a dictionary
        of all generated artifacts.
        """
        current_ir = self.ir

        if "copy_propagation" in self.phases_to_run:
            current_ir = run_copy_propagation(current_ir)
            self.artifacts["copy_propagation"] = current_ir

        if "identity_elimination" in self.phases_to_run:
            current_ir = run_identity_elimination(current_ir)
            self.artifacts["identity_elimination"] = current_ir

        if "constant_folding" in self.phases_to_run:
            current_ir = run_constant_folding(current_ir)
            self.artifacts["constant_folding"] = current_ir

        if "dead_code_elimination" in self.phases_to_run:
            current_ir = run_dce(current_ir, self.model)
            self.artifacts["dead_code_elimination"] = current_ir

        return self.artifacts


def optimize_ir(ir: List[Dict[str, Any]], model: FileSemanticModel, stop_after_phase: str) -> Dict[str, Any]:
    """
    High-level entry point for the IR optimization stage.
    """
    all_phases = ["copy_propagation", "identity_elimination", "constant_folding", "dead_code_elimination"]

    try:
        stop_index = all_phases.index(stop_after_phase)
        phases_to_run = all_phases[: stop_index + 1]
    except ValueError:
        phases_to_run = all_phases

    optimizer = IROptimizer(ir, model, phases_to_run)
    return optimizer.optimize()
