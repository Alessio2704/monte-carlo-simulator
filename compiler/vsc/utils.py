"""
Utility functions for the ValuaScript compiler, including terminal coloring,
error formatting, executable searching, and artifact serialization.
"""

import json
from typing import Dict, Any
from lark import Token
from .parser.parser import _StringLiteral


class TerminalColors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[033m"


class CompilerArtifactEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for compiler artifacts. It handles special types
    like Tokens, sets, and our custom _StringLiteral class.
    """

    def default(self, o):
        if isinstance(o, Token):
            return o.value
        if isinstance(o, set):
            return list(o)
        if isinstance(o, _StringLiteral):
            # Encode _StringLiteral as a dictionary to preserve its type info
            return {"__type__": "_StringLiteral", "value": o.value}
        if hasattr(o, "__dict__"):
            return o.__dict__
        # Fallback for any other types
        return str(o)


def compiler_artifact_decoder_hook(d: Dict) -> Any:
    """
    A custom object_hook for json.load() to "rehydrate" _StringLiteral
    objects from their special dictionary representation.
    """
    if d.get("__type__") == "_StringLiteral":
        return _StringLiteral(d.get("value"))
    return d
