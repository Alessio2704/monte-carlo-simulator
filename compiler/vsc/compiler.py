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
from .ir_optimizer import optimize_ir
from .optimizer.ir_validator import IRValidator, IRValidationError

# from .bytecode_generator import generate_bytecode


# A custom JSON encoder will be needed for complex objects
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
            return {"symbols": o.symbols, "parent": "<PARENT_SCOPE_OMITTED_FOR_SERIALIZATION>" if o.parent else None}
        if hasattr(o, "__dict__"):
            return o.__dict__
        return str(o)


class CompilationPipeline:
    """
    Orchestrates the full compilation process.
    """

    def __init__(self, source_content: str, file_path: Optional[str], dump_stages: List[str] = [], optimize: bool = False, stop_after_stage: Optional[str] = None):
        self.source_content = source_content
        self.file_path = os.path.abspath(file_path) if file_path else "<stdin>"
        self.dump_stages = dump_stages
        self.optimize = optimize
        self.stop_after_stage = stop_after_stage
        self.artifacts = {}
        self.model = None

    def run(self) -> Dict[str, Any]:
        """Executes the compilation pipeline."""

        ast = self._run_stage("ast", parse_valuascript, self.source_content)
        if self.stop_after_stage == "ast":
            return ast

        symbol_table = self._run_stage("symbol_table", discover_symbols, ast, self.file_path)
        if self.stop_after_stage == "symbol_table":
            return symbol_table

        enriched_symbol_table = self._run_stage("type_inference", infer_types_and_taint, symbol_table)
        if self.stop_after_stage == "type_inference":
            return enriched_symbol_table

        validated_symbol_table = self._run_stage("semantic_validation", validate_semantics, enriched_symbol_table)
        if self.stop_after_stage == "semantic_validation":
            return validated_symbol_table

        self.model = validated_symbol_table

        # STAGE 5: Intermediate Representation (IR) Generation
        ir = self._run_stage("ir", generate_ir, self.model)
        # 2. Validate the raw IR immediately after generation.
        self._validate_ir(ir, "generation")
        if self.stop_after_stage == "ir":
            return ir

        # --- STAGE 6: Optimization Phases ---
        optimization_phases = ["copy_propagation", "tuple_forwarding", "identity_elimination", "constant_folding", "dead_code_elimination"]
        final_opt_stage_name = "optimized_ir"

        if self.stop_after_stage in optimization_phases or self.stop_after_stage == final_opt_stage_name:
            last_phase_to_run = self.stop_after_stage
            if last_phase_to_run == final_opt_stage_name:
                last_phase_to_run = optimization_phases[-1]

            optimization_artifacts = self._run_stage(self.stop_after_stage, self._run_optimization_phases, ir, self.model, last_phase_to_run)

            return optimization_artifacts.get(last_phase_to_run, {})

        return ir

    def _run_optimization_phases(self, ir, model, last_phase_to_run):
        """
        Helper to run the optimization pipeline and validate at each step.
        """
        all_phases = ["copy_propagation", "tuple_forwarding", "identity_elimination", "constant_folding", "dead_code_elimination"]
        stop_index = all_phases.index(last_phase_to_run)
        phases_to_run = all_phases[: stop_index + 1]

        from .optimizer.copy_propagation import run_copy_propagation
        from .optimizer.tuple_forwarding import run_tuple_forwarding
        from .optimizer.identity_elimination import run_identity_elimination
        from .optimizer.constant_folding import run_constant_folding
        from .optimizer.dead_code_elimination import run_dce

        optimization_artifacts = {}
        current_ir = ir

        if "copy_propagation" in phases_to_run:
            current_ir = run_copy_propagation(current_ir)
            self._validate_ir(current_ir, "copy_propagation")
            optimization_artifacts["copy_propagation"] = current_ir

        if "tuple_forwarding" in phases_to_run:
            current_ir = run_tuple_forwarding(current_ir)
            self._validate_ir(current_ir, "tuple_forwarding")
            optimization_artifacts["tuple_forwarding"] = current_ir

        if "identity_elimination" in phases_to_run:
            current_ir = run_identity_elimination(current_ir)
            self._validate_ir(current_ir, "identity_elimination")
            optimization_artifacts["identity_elimination"] = current_ir

        if "constant_folding" in phases_to_run:
            current_ir = run_constant_folding(current_ir)
            self._validate_ir(current_ir, "constant_folding")
            optimization_artifacts["constant_folding"] = current_ir

        if "dead_code_elimination" in phases_to_run:
            current_ir = run_dce(current_ir, model)
            self._validate_ir(current_ir, "dead_code_elimination")
            optimization_artifacts["dead_code_elimination"] = current_ir

        return optimization_artifacts

    def _run_stage(self, stage_name: str, stage_func, *args, **kwargs):
        """Executes a single stage, stores its artifact, and handles dumping."""
        try:
            if stage_name in ("type_inference", "semantic_validation"):
                import copy

                args = (copy.deepcopy(args[0]),)

            result = stage_func(*args, **kwargs)
            self.artifacts[stage_name] = result

            if stage_name in self.dump_stages:
                artifact_to_save = result
                if stage_name == "semantic_validation":
                    artifact_to_save = args[0]
                elif stage_name in ("copy_propagation", "tuple_forwarding", "identity_elimination", "constant_folding", "dead_code_elimination"):
                    artifact_to_save = result.get(stage_name)
                elif stage_name == "optimized_ir":
                    last_phase = "dead_code_elimination"
                    artifact_to_save = result.get(last_phase)

                self.save_artifact(stage_name, artifact_to_save)
            return result
        except ValuaScriptError as e:
            raise e
        except Exception as e:
            import traceback

            traceback.print_exc()
            # Re-raise as an internal compiler error for clarity
            raise Exception(f"An unexpected internal error occurred in the '{stage_name}' stage: {e}") from e

    def save_artifact(self, name: str, data: Any):
        """Saves an intermediate artifact to a JSON file."""
        if not self.file_path or self.file_path == "<stdin>":
            base_name = "stdin_output"
        else:
            base_name = os.path.splitext(self.file_path)[0]

        output_path = f"{base_name}.{name}.json"
        print(f"--- Saving artifact '{name}' to {output_path} ---")
        try:
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, cls=CompilerArtifactEncoder)
        except Exception as e:
            print(f"Error: Could not save artifact '{name}': {e}")

    def _validate_ir(self, ir: List[Dict[str, Any]], producing_stage: str):
        """
        Internal helper to run the validator and raise a clear internal error.
        """
        try:
            IRValidator(ir).validate()
        except IRValidationError as e:
            # This is an internal compiler bug, so we raise a generic but informative exception.
            raise Exception(f"Internal Compiler Error: The '{producing_stage}' stage produced a logically invalid IR.\n" f"This is a bug in the compiler. Details:\n{e}") from e


def compile_valuascript(script_content: str, file_path=None, dump_stages=[], optimize=False, stop_after_stage=None):
    """High-level entry point for the compilation pipeline."""
    pipeline = CompilationPipeline(script_content, file_path, dump_stages, optimize, stop_after_stage)
    return pipeline.run()
