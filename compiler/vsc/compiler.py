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
        if self.stop_after_stage == "ir":
            return ir

        # --- STAGE 6: Optimization Phases ---
        optimization_phases = ["copy_propagation", "identity_elimination", "constant_folding"]
        final_opt_stage_name = "optimized_ir"

        # Determine if we are stopping within the optimization block
        if self.stop_after_stage in optimization_phases or self.stop_after_stage == final_opt_stage_name:

            # Determine the last phase to run
            last_phase_to_run = self.stop_after_stage
            if last_phase_to_run == final_opt_stage_name:
                last_phase_to_run = optimization_phases[-1]

            # Run the optimizer. Note: the stage name passed to _run_stage is for artifact saving purposes.
            optimization_artifacts = self._run_stage(self.stop_after_stage, optimize_ir, ir, self.model, stop_after_phase=last_phase_to_run)

            # Extract the correct artifact to return, which is the result of the very last phase that ran.
            return optimization_artifacts.get(last_phase_to_run, {})

        # Default case: no optimization, return stage 5 IR
        return ir

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
                # For validation, the result is the same table, so we save the input
                if stage_name == "semantic_validation":
                    artifact_to_save = args[0]
                # For optimization phases, the result is a dict of artifacts. We save the specific one requested.
                elif stage_name in ("copy_propagation", "identity_elimination", "constant_folding"):
                    artifact_to_save = result.get(stage_name)
                # For the final 'optimized_ir' stage, the result is the output of the last phase.
                elif stage_name == "optimized_ir":
                    last_phase = "constant_folding"
                    artifact_to_save = result.get(last_phase)

                self.save_artifact(stage_name, artifact_to_save)
            return result
        except ValuaScriptError as e:
            raise e
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise Exception(f"An unexpected error occurred in the '{stage_name}' stage: {e}") from e

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


def compile_valuascript(script_content: str, file_path=None, dump_stages=[], optimize=False, stop_after_stage=None):
    """High-level entry point for the compilation pipeline."""
    pipeline = CompilationPipeline(script_content, file_path, dump_stages, optimize, stop_after_stage)
    return pipeline.run()
