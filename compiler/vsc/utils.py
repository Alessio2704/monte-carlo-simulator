"""
Utility functions for the ValuaScript compiler, including terminal coloring,
and a robust JSON artifact serializer.
"""

import json

from lark import Token
from pydantic import BaseModel


class TerminalColors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[033m"


class CompilerArtifactEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, BaseModel):
            return o.model_dump(mode="json")
        if isinstance(o, Token):
            return o.value
        if isinstance(o, set):
            return list(o)
        return super().default(o)
