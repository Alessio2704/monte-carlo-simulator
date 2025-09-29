from typing import Dict

from vsc.parser.core.classes import Root
from vsc.parser.core.parser import parse_valuascript


class ModuleLoader:
    """
    Responsible for loading, parsing, and caching ValuaScript modules from disk.
    This class is the boundary between the compiler's pure logic and the file system.
    """

    def __init__(self):
        # The cache ensures we only ever parse a single file once.
        self._ast_cache: Dict[str, Root] = {}

    def load(self, absolute_path: str) -> Root:
        """
        Loads and parses a ValuaScript file from an absolute path.
        Returns a cached AST if the file has already been loaded.
        """
        if absolute_path in self._ast_cache:
            return self._ast_cache[absolute_path]

        try:
            with open(absolute_path, "r", encoding="utf-8") as f:
                content = f.read()

            ast = parse_valuascript(content, file_path=absolute_path)
            self._ast_cache[absolute_path] = ast
            return ast
        except FileNotFoundError:
            # Re-raise with a more specific context if needed, or let the caller handle it.
            raise FileNotFoundError(f"Compiler could not find file at: {absolute_path}")
