from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Union

"""
Defines the core data structures for the ValuaScript Semantic Model.
These structures are created from the raw AST and are progressively
enriched during the semantic analysis and validation phases.
"""


@dataclass
class Location:
    """Represents a location in a source file."""

    file_path: str
    line: int
    column: int


@dataclass
class Symbol:
    """Base class for any named entity in the code."""

    name: str
    location: Location
    inferred_type: Optional[Union[str, List[str]]] = None
    is_stochastic: bool = False


@dataclass
class ExpressionNode:
    """Represents an expression, which will be resolved to a value."""

    raw_node: Dict[str, Any]
    inferred_type: Optional[str] = None
    is_stochastic: bool = False


@dataclass
class VariableSymbol(Symbol):
    """Represents a declared variable."""

    value_node: Optional[ExpressionNode] = None


@dataclass
class ConditionalNode(Symbol):
    """Represents a conditional if/then/else assignment."""

    condition_node: Optional[ExpressionNode] = None
    then_node: Optional[ExpressionNode] = None
    else_node: Optional[ExpressionNode] = None


@dataclass
class FunctionParameter:
    """Represents a parameter in a function definition."""

    name: str
    type: str
    location: Location


@dataclass
class FunctionSymbol(Symbol):
    """Represents a user-defined function."""

    parameters: List[FunctionParameter] = field(default_factory=list)
    return_type: Union[str, List[str]] = "scalar"
    docstring: Optional[str] = None
    body: "Scope" = field(default_factory=lambda: Scope())
    return_node: Optional[ExpressionNode] = None
    ast_body: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Scope:
    """Represents a lexical scope containing symbols."""

    symbols: Dict[str, Symbol] = field(default_factory=dict)
    parent: Optional["Scope"] = None


@dataclass
class FileSemanticModel:
    """The top-level data structure representing a single parsed .vs file."""

    file_path: str
    global_scope: Scope = field(default_factory=Scope)
    imports: Dict[str, "FileSemanticModel"] = field(default_factory=dict)
    is_module: bool = False
    directives: Dict[str, Any] = field(default_factory=dict)
