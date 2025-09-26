"""
Utility functions for the ValuaScript compiler, including terminal coloring,
and a robust JSON artifact serializer.
"""

import json
from dataclasses import is_dataclass, asdict
from lark import Token


class TerminalColors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[033m"


class CompilerArtifactEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for compiler artifacts. It correctly serializes:
    - All dataclass objects (by converting them to dictionaries).
    - Lark Token objects (by taking their string value).
    - Sets (by converting them to lists).
    """

    def default(self, o):
        # The primary mechanism: if the object is a dataclass, use the
        # standard library's asdict() helper to convert it to a dictionary.
        # This is recursive and handles nested dataclasses perfectly.
        if is_dataclass(o):
            return asdict(o)

        # Fallbacks for other common types found during compilation.
        if isinstance(o, Token):
            return o.value
        if isinstance(o, set):
            return list(o)

        # This will now correctly handle any other object types by calling
        # the base class's method, which will raise a TypeError if it's
        # not a standard JSON-serializable type.
        return super().default(o)
