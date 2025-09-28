import json
import os
from typing import Any, Dict, List, Optional

from vsc.parser.core.parser import parse_valuascript

from .exceptions import ValuaScriptError
from .utils import CompilerArtifactEncoder


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
        ast = self._run_stage("ast", parse_valuascript, self.source_content, self.file_path)
        if self.stop_after_stage == "ast":
            return ast

        # Until future stages
        return ast

    def _run_stage(self, stage_name: str, stage_func, *args, **kwargs):
        """
        Executes a single stage, validates its output where applicable,
        stores its artifact, and handles dumping to a file.
        """
        try:

            result = stage_func(*args, **kwargs)
            self.artifacts[stage_name] = result

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


def compile_valuascript(script_content: str, file_path: Optional[str] = None, dump_stages: List[str] = [], stop_after_stage: Optional[str] = None):
    """
    High-level entry point for the compilation pipeline. It creates and runs
    a CompilationPipeline instance.
    """
    pipeline = CompilationPipeline(script_content, file_path, dump_stages, stop_after_stage)
    return pipeline.run()
