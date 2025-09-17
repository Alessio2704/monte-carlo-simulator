import os
import json
from typing import List, Optional, Dict, Any
from .exceptions import ValuaScriptError
from .parser import parse_valuascript
from .symbol_discovery import discover_symbols
from .type_inferrer import infer_types_and_taint
from .semantic_validator import validate_semantics
from .ir_generator import generate_ir
from .ir_optimizer import optimize_ir
from .bytecode_generator import generate_bytecode


# A custom JSON encoder will be needed for complex objects like Lark Tokens
class CompilerArtifactEncoder(json.JSONEncoder):
    def default(self, o):
        from .data_structures import Scope

        if isinstance(o, set):
            return list(o)

        if isinstance(o, Scope):
            return {"symbols": o.symbols, "parent": "<PARENT_SCOPE_OMITTED_FOR_SERIALIZATION>" if o.parent else None}

        if hasattr(o, "__dict__"):
            if type(o).__name__ == "Token":
                return {"type": "Token", "value": o.value}
            return o.__dict__

        return str(o)


class CompilationPipeline:
    """
    Orchestrates the full compilation process, managing the flow through
    each stage and allowing for the inspection of intermediate artifacts.
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
        """Executes the compilation pipeline, halting after the specified stage if requested."""

        # STAGE 1: Parsing
        ast = self._run_stage("ast", parse_valuascript, self.source_content)
        if self.stop_after_stage == "ast":
            return ast

        # STAGE 2: Symbol Discovery
        symbol_table = self._run_stage("symbol_table", discover_symbols, ast, self.file_path)
        if self.stop_after_stage == "symbol_table":
            return symbol_table

        # STAGE 3: Type Inference & Stochasticity Tainting
        enriched_symbol_table = self._run_stage("type_inference", infer_types_and_taint, symbol_table)
        if self.stop_after_stage == "type_inference":
            return enriched_symbol_table

        # --- STAGE 4: Semantic Validation ---
        validated_symbol_table = self._run_stage("semantic_validation", validate_semantics, enriched_symbol_table)
        if self.stop_after_stage == "semantic_validation":
            return validated_symbol_table

        # Store the final validated model for later stages
        self.model = validated_symbol_table

        # STAGE 5: Intermediate Representation (IR) Generation
        ir = self._run_stage("ir", generate_ir, self.model)
        if self.stop_after_stage == "ir":
            return ir

        # STAGE 6: Optimization
        optimized_ir = self._run_stage("optimized_ir", optimize_ir, ir, self.model, self.optimize)
        if self.stop_after_stage == "optimized_ir":
            return optimized_ir

        # STAGE 7: Bytecode Generation (Linking)
        final_recipe = self._run_stage("recipe", generate_bytecode, optimized_ir, self.model)

        return final_recipe

    def _run_stage(self, stage_name: str, stage_func, *args, **kwargs):
        """Executes a single stage, stores its artifact, and handles dumping."""
        try:
            # For stages that are enriching a structure, we pass a copy
            if stage_name in ("type_inference", "semantic_validation"):
                import copy

                args = (copy.deepcopy(args[0]),)

            result = stage_func(*args, **kwargs)
            self.artifacts[stage_name] = result
            if stage_name in self.dump_stages:
                # For validation, the artifact is the table it successfully validated
                if stage_name == "semantic_validation":
                    self.save_artifact(stage_name, args[0])
                else:
                    self.save_artifact(stage_name, result)
            return result
        except ValuaScriptError as e:
            raise e
        except Exception as e:
            raise Exception(f"An unexpected error occurred in the '{stage_name}' stage: {e}") from e

    def save_artifact(self, name: str, data: Any):
        """Saves an intermediate artifact to a JSON file."""
        if not self.file_path or self.file_path == "<stdin>":
            base_name = "stdin_output"
        else:
            base_name = os.path.splitext(self.file_path)[0]

        output_path = f"{base_name}.{name}.json"

        try:
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, cls=CompilerArtifactEncoder)
            print(f"--- Artifact '{name}' saved to {output_path} ---")
        except Exception as e:
            print(f"Error: Could not save artifact '{name}': {e}")


def compile_valuascript(script_content: str, file_path=None, dump_stages=[], optimize=False, stop_after_stage=None):
    """
    High-level entry point for the compilation pipeline.
    """
    pipeline = CompilationPipeline(script_content, file_path, dump_stages, optimize, stop_after_stage)
    return pipeline.run()
