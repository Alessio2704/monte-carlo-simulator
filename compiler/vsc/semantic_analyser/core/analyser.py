from typing import Any, Dict, List, Optional

from vsc.parser.core.classes import Root

from .import_resolver import resolve_imports


class SemanticAnalyser:
    """
    Orchestrates the semantic analysis phase of the compiler.
    """

    def __init__(
        self,
        main_ast: Root,
        dump_stages: List[str] = [],
        stop_after_stage: Optional[str] = None,
    ):
        self.main_ast = main_ast
        self.dump_stages = dump_stages
        self.stop_after_stage = stop_after_stage
        self.artifacts: Dict[str, Any] = {}
        self.results: List[Any] = []

    def run(self) -> Any:
        """Executes the semantic analysis pipeline."""

        # --- Stage 2a: Import Resolution ---
        # The input is the main AST passed to the constructor.
        self._run_stage("semantic_analyser_imports", resolve_imports, self.main_ast)
        if self.stop_after_stage == "semantic_analyser_imports":
            return self.results[-1]

        # --- Future Stages (2b, 2c) will go here ---
        # The input would be `self.results[-1]`

        # If the pipeline completes, return the final artifact
        return self.results[-1]

    def _run_stage(self, stage_name: str, stage_func, *args, **kwargs) -> Any:
        """Executes a single stage, stores its artifact, and returns the result."""
        result = stage_func(*args, **kwargs)
        self.artifacts[stage_name] = result
        self.results.append(result)  # Append to this pipeline's results chain
        return result
