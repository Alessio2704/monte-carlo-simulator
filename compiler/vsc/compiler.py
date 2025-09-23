import os
import json
from typing import List, Optional, Dict, Any
from lark import Token
from .exceptions import ValuaScriptError
from .parser import parse_valuascript, _StringLiteral
from .symbol_discovery import discover_symbols
from .type_inferrer import infer_types_and_taint
from .semantic_validator import validate_semantics
from .ir_generator import generate_ir
from .optimizer.copy_propagation import run_copy_propagation
from .optimizer.tuple_forwarding import run_tuple_forwarding
from .optimizer.alias_resolver import run_alias_resolver
from .optimizer.constant_folding import run_constant_folding
from .optimizer.dead_code_elimination import run_dce
from .ir_partitioner import partition_ir


from .bytecode_generator import BytecodeGenerator
from .optimizer.ir_validator import IRValidator, IRValidationError


class CompilerArtifactEncoder(json.JSONEncoder):
    def default(self, o):
        from .data_structures import Scope

        if isinstance(o, Token):
            return o.value
        if isinstance(o, set):
            return list(o)
        if isinstance(o, _StringLiteral):
            return o.value
        if isinstance(o, Scope):
            # Avoid circular references and excessive nesting in JSON output
            return {"symbols": o.symbols, "parent": "<PARENT_SCOPE_OMITTED_FOR_SERIALIZATION>" if o.parent else None}
        if hasattr(o, "__dict__"):
            return o.__dict__
        # Fallback for any other types
        return str(o)


class CompilationPipeline:
    """
    Orchestrates the full compilation process from source code to final recipe.
    """

    def __init__(self, source_content: str, file_path: Optional[str], dump_stages: List[str] = [], stop_after_stage: Optional[str] = None):
        self.source_content = source_content
        self.file_path = os.path.abspath(file_path) if file_path else "<stdin>"
        self.dump_stages = dump_stages
        self.stop_after_stage = stop_after_stage
        self.artifacts: Dict[str, Any] = {}
        self.model: Optional[Dict[str, Any]] = None

    def run(self) -> Dict[str, Any]:
        """Executes the compilation pipeline."""

        # --- Stage 1: Parsing ---
        ast = self._run_stage("ast", parse_valuascript, self.source_content)
        if self.stop_after_stage == "ast":
            return ast

        # --- Stage 2: Symbol Discovery ---
        symbol_table = self._run_stage("symbol_table", discover_symbols, ast, self.file_path)
        if self.stop_after_stage == "symbol_table":
            return symbol_table

        # --- Stage 3: Type Inference & Tainting ---
        enriched_symbol_table = self._run_stage("type_inference", infer_types_and_taint, symbol_table)
        if self.stop_after_stage == "type_inference":
            return enriched_symbol_table

        # --- Stage 4: Semantic Validation ---
        validated_model = self._run_stage("semantic_validation", validate_semantics, enriched_symbol_table)
        self.model = validated_model
        if self.stop_after_stage == "semantic_validation":
            return validated_model

        # --- Stage 5: IR Generation ---
        ir = self._run_stage("ir", generate_ir, self.model)
        if self.stop_after_stage == "ir":
            return ir

        # --- Stage 6: IR Optimization (multiple phases) ---
        optimization_artifacts = self._run_optimization_phases(ir, self.model)

        # Check if we should stop after a specific optimization phase
        if self.stop_after_stage in optimization_artifacts:
            return optimization_artifacts[self.stop_after_stage]

        optimized_ir = optimization_artifacts.get("dead_code_elimination", ir)
        if self.stop_after_stage == "optimized_ir":
            self.save_artifact("optimized_ir", optimized_ir)
            return optimized_ir

        # --- Stage 7: IR Partitioning ---
        partitioned_ir = self._run_stage("ir_partitioning", partition_ir, optimized_ir, self.model)
        if self.stop_after_stage == "ir_partitioning":
            return partitioned_ir

        # --- Stage 8: Bytecode Generation (multiple phases) ---
        bytecode_artifacts = self._run_bytecode_phases(partitioned_ir, self.model)
        if self.stop_after_stage in bytecode_artifacts:
            return bytecode_artifacts[self.stop_after_stage]

        recipe = bytecode_artifacts.get("recipe")
        if self.stop_after_stage == "recipe":
            return recipe

        # If no stop_after_stage is specified, the final recipe is the product.
        return recipe

    def _run_optimization_phases(self, ir: List[Dict[str, Any]], model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to run the optimization pipeline, validating and storing the
        artifact from each phase.
        """
        optimization_artifacts = {}
        current_ir = ir

        # The sequence of optimization phases
        phases = {
            "copy_propagation": run_copy_propagation,
            "tuple_forwarding": run_tuple_forwarding,
            "alias_resolver": run_alias_resolver,
            "constant_folding": run_constant_folding,
            "dead_code_elimination": lambda ir_arg: run_dce(ir_arg, model),
        }

        for name, func in phases.items():
            current_ir = self._run_stage(name, func, current_ir)
            optimization_artifacts[name] = current_ir
            # If the user wants to stop after this phase, we don't run subsequent ones.
            if self.stop_after_stage == name:
                break

        return optimization_artifacts

    def _run_bytecode_phases(self, partitioned_ir: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Helper to run the bytecode generation pipeline, storing the artifact
        from each internal sub-phase.
        """
        bytecode_artifacts = {}

        # This stateful generator object will be used across all sub-phases.
        generator = BytecodeGenerator(partitioned_ir, model)

        # The sequence of bytecode generation sub-phases.
        # The key is the stage name from the CLI, the value is the method to call.
        phases = {
            "bytecode_resource_allocation": generator.run_phase_a_resource_allocation,
            "bytecode_ir_lowering": generator.run_phase_b_ir_lowering,
            "bytecode_code_emission": generator.run_phase_c_code_emission,
            "recipe": generator.run_final_assembly,
        }

        for name, phase_func in phases.items():
            # We use _run_stage to handle artifact saving and error wrapping.
            artifact = self._run_stage(name, phase_func)

            # The artifact for 8b is now a dictionary containing both the
            # lowered IR and the updated registries.
            if name == "bytecode_ir_lowering":
                # We need to validate the IR *inside* the combined artifact
                if "lowered_ir" in artifact:
                    self._validate_ir_partition(artifact["lowered_ir"], "bytecode_ir_lowering")

            bytecode_artifacts[name] = artifact

            if self.stop_after_stage == name:
                break

        return bytecode_artifacts

    def _validate_ir_partition(self, result: Dict, stage_name: str):
        """Helper to validate a partitioned IR structure."""
        if isinstance(result, dict) and "pre_trial_steps" in result:
            pre_trial_validator = IRValidator(result.get("pre_trial_steps", []))
            pre_trial_validator.validate()

            per_trial_validator = IRValidator(result.get("per_trial_steps", []))
            # Prime the per-trial validator with variables defined in the pre-trial phase
            per_trial_validator.defined_vars = pre_trial_validator.defined_vars.copy()
            per_trial_validator.validate()

    def _run_stage(self, stage_name: str, stage_func, *args, **kwargs):
        """
        Executes a single stage, validates its output where applicable,
        stores its artifact, and handles dumping to a file.
        """
        try:
            # Deepcopy inputs for stages that modify data structures in place
            if stage_name in ("type_inference", "semantic_validation"):
                import copy

                args = (copy.deepcopy(args[0]),)

            result = stage_func(*args, **kwargs)
            self.artifacts[stage_name] = result

            if stage_name.startswith("ir") or stage_name in ["copy_propagation", "tuple_forwarding", "alias_resolver", "constant_folding", "dead_code_elimination", "ir_partitioning"]:
                self._validate_ir_partition(result, stage_name)
            elif isinstance(result, list):
                self._validate_ir(result, stage_name)

            if stage_name in self.dump_stages:
                self.save_artifact(stage_name, result)
            return result

        except ValuaScriptError as e:
            # Re-raise compiler errors to be handled by the CLI
            raise e
        except Exception as e:
            # Wrap unexpected errors for clearer reporting
            import traceback

            traceback.print_exc()
            raise Exception(f"An unexpected internal error occurred in the '{stage_name}' stage: {e}") from e

    def save_artifact(self, name: str, data: Any):
        """Saves an intermediate artifact to a JSON file."""
        if self.file_path == "<stdin>":
            base_name = "stdin_output"
        else:
            base_name = os.path.splitext(self.file_path)[0]

        output_path = f"{base_name}.{name}.json"
        print(f"--- Saving artifact '{name}' to {output_path} ---")
        try:
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, sort_keys=False, cls=CompilerArtifactEncoder)
        except Exception as e:
            print(f"Error: Could not save artifact '{name}': {e}")

    def _validate_ir(self, ir: List[Dict[str, Any]], producing_stage: str):
        """Internal helper to run the validator and raise a clear internal error."""
        try:
            IRValidator(ir).validate()
        except IRValidationError as e:
            # This indicates a bug in the compiler itself.
            raise Exception(f"Internal Compiler Error: The '{producing_stage}' stage produced a logically invalid IR.\n" f"This is a bug in the compiler. Details:\n{e}") from e


def compile_valuascript(script_content: str, file_path: Optional[str] = None, dump_stages: List[str] = [], stop_after_stage: Optional[str] = None):
    """
    High-level entry point for the compilation pipeline. It creates and runs
    a CompilationPipeline instance.
    """
    pipeline = CompilationPipeline(script_content, file_path, dump_stages, stop_after_stage)
    return pipeline.run()
