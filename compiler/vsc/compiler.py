import json
import os
from typing import Any, Dict, List, Optional, Type

from vsc.parser.core.parser import parse_valuascript
from vsc.semantic_analyser.core.analyser import SemanticAnalyser

from .exceptions import ValuaScriptError
from .utils import CompilerArtifactEncoder


class CompilationPipeline:
    """
    Orchestrates the full compilation process from source code to final recipe.
    This class manages the flow of data between different compiler stages.
    """

    def __init__(
        self,
        source_content: str,
        file_path: Optional[str],
        dump_stages: List[str] = [],
        stop_after_stage: Optional[str] = None,
    ):
        self.source_content = source_content
        self.file_path = os.path.abspath(file_path) if file_path else "<stdin>"
        self.dump_stages = dump_stages
        self.stop_after_stage = stop_after_stage
        self.artifacts: Dict[str, Any] = {}
        self.results: List[Any] = []

    def run(self) -> Any:
        """
        Executes the compilation pipeline stage by stage.
        The final artifact from each stage is passed as input to the next.
        """
        try:
            # --- Stage 1: Parsing ---
            # The input is the raw source code content
            self._run_simple_stage("ast", parse_valuascript, self.source_content, self.file_path)
            if self.stop_after_stage == "ast":
                return self.results[-1]

            # --- Stage 2: Semantic Analysis (as a Sub-Pipeline) ---
            # The input is the AST from the previous stage
            self._run_sub_pipeline("semantic_analyser", SemanticAnalyser, self.results[-1])
            if self.stop_after_stage == "semantic_analyser":
                return self.results[-1]

            # --- Future Stages will go here ---
            # The input would be `self.results[-1]`

            # If the pipeline completes, return the final artifact
            return self.results[-1]

        except ValuaScriptError as e:
            raise e
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise Exception(f"An unexpected internal error occurred: {e}") from e

    def _run_simple_stage(self, name: str, func, *args, **kwargs) -> Any:
        """Runs a single function as a stage, storing and returning its result."""
        result = func(*args, **kwargs)
        self.artifacts[name] = result
        self.results.append(result)  # Append to the results chain
        if name in self.dump_stages:
            self.save_artifact(name, result)
        return result

    def _run_sub_pipeline(self, name: str, pipeline_class: Type, input_artifact: Any) -> Any:
        """Runs a complex stage that has its own internal pipeline."""
        sub_pipeline = pipeline_class(input_artifact, self.dump_stages, self.stop_after_stage)
        final_product = sub_pipeline.run()

        self.artifacts.update(sub_pipeline.artifacts)
        self.results.append(final_product)  # Append the final product of the sub-pipeline

        for stage_name, artifact_data in sub_pipeline.artifacts.items():
            if stage_name in self.dump_stages:
                self.save_artifact(stage_name, artifact_data)

        # If -c argument is a whole number it means we are running the full sub-pipeline
        if self.stop_after_stage == name:
            self.save_artifact(stage_name, final_product)

        return final_product

    def save_artifact(self, name: str, data: Any):
        """Saves an intermediate artifact to a JSON file with a user-friendly name."""

        if self.file_path == "<stdin>":
            base_name = "stdin_output"
        else:
            base_name = os.path.splitext(self.file_path)[0]

        output_path = f"{base_name}.{name}.json"

        print(f"--- Saving artifact '{name}' to {output_path} ---")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, sort_keys=False, cls=CompilerArtifactEncoder)
        except Exception as e:
            print(f"Error: Could not save artifact '{name}': {e}")


def compile_valuascript(
    script_content: str,
    file_path: Optional[str] = None,
    dump_stages: List[str] = [],
    stop_after_stage: Optional[str] = None,
):
    """High-level entry point for the compilation pipeline."""
    pipeline = CompilationPipeline(script_content, file_path, dump_stages, stop_after_stage)
    return pipeline.run()
