from typing import Dict, Any, List

from .bytecode_generation.resource_allocator import ResourceAllocator
from .bytecode_generation.ir_lowerer import IRLowerer


class BytecodeGenerator:
    """
    Orchestrates the multi-phase process of converting the partitioned,
    optimized IR into the final integer-based bytecode recipe for the
    ValuaScript Execution Engine (vse).

    This class is stateful; each phase consumes data from the previous phase.
    """

    def __init__(self, partitioned_ir: Dict[str, List[Dict[str, Any]]], model: Dict[str, Any]):
        self.partitioned_ir = partitioned_ir
        self.model = model

        # --- Artifacts from each phase, stored on the instance ---
        self.registries: Dict[str, Any] = {}
        self.lowered_ir: Dict[str, List[Dict[str, Any]]] = {}
        self.emitted_code: Dict[str, List[Dict[str, Any]]] = {}

    def generate(self) -> Dict[str, Any]:
        """
        Convenience method to run the entire bytecode generation pipeline.
        The main compiler driver may call the sub-phases individually.
        """
        self.run_phase_a_resource_allocation()
        self.run_phase_b_ir_lowering()
        self.run_phase_c_code_emission()
        return self.run_final_assembly()

    def run_phase_a_resource_allocation(self) -> Dict[str, Any]:
        """
        PHASE 8a: Scans the entire IR to build a complete inventory of
        all variables and constants.
        """
        allocator = ResourceAllocator(self.partitioned_ir, self.model)
        self.registries = allocator.allocate()
        return self.registries

    def run_phase_b_ir_lowering(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        PHASE 8b: Converts the high-level IR into a flat, linear sequence of
        simple, machine-like operations.
        """
        # This phase consumes the registries from 8a and modifies them in place
        # as it discovers new temporary variables during expression lifting.
        lowerer = IRLowerer(self.partitioned_ir, self.registries, self.model)
        self.lowered_ir = lowerer.lower()
        return self.lowered_ir

    def run_phase_c_code_emission(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        PHASE 8c: Translates the final, lowered IR into the integer-based
        instruction format.
        """
        # --- PLACEHOLDER ---
        # In the future, this will instantiate and run the Code Emitter.
        print("--- NOTE: Stage 8c (Code Emission) is not yet implemented. ---")
        self.emitted_code = {
            "pre_trial_instructions": [],
            "per_trial_instructions": [],
        }
        return self.emitted_code

    def run_final_assembly(self) -> Dict[str, Any]:
        """
        Assembles the final JSON recipe from the artifacts of all previous phases.
        """
        # This will assemble the final recipe structure as defined in the design doc.
        final_recipe = {
            "simulation_config": {"num_trials": 10000},  # Placeholder
            "variable_register_counts": self.registries.get("variable_register_counts", {}),
            "constants": self.registries.get("constant_pools", {}),
            "pre_trial_instructions": self.emitted_code.get("pre_trial_instructions", []),
            "per_trial_instructions": self.emitted_code.get("per_trial_instructions", []),
        }
        return final_recipe
