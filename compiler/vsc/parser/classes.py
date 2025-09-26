"""
Defines the formal data structures (contracts) for the Abstract Syntax Tree (AST)
produced by the parser stage.

Each node is represented by a dataclass and includes a `Span` object to track its
location in the source code, enabling precise error reporting in later stages.
"""

from dataclasses import dataclass
from typing import List, Union, Optional

# --- Core Data Structures ---


@dataclass
class Span:
    """Represents a location in the source code for precise error reporting."""

    s_line: int
    s_col: int
    e_line: int
    e_col: int
    file_path: Optional[str] = None


@dataclass
class ASTNode:
    """A base class for all AST nodes, ensuring they have a span."""

    span: Span


# --- Literals and Identifiers ---


@dataclass
class NumberLiteral(ASTNode):
    value: Union[int, float]


@dataclass
class StringLiteral(ASTNode):
    value: str


@dataclass
class BooleanLiteral(ASTNode):
    value: bool


@dataclass
class Identifier(ASTNode):
    name: str


@dataclass
class VectorLiteral(ASTNode):
    items: List["Node"]  # Using 'Node' for flexible typing


# --- Expressions ---
# A generic type hint for any expression node
Expression = Union[NumberLiteral, StringLiteral, BooleanLiteral, Identifier, VectorLiteral, "TupleLiteral", "FunctionCall", "ElementAccess", "DeleteElement", "ConditionalExpression"]

@dataclass
class TupleLiteral(ASTNode):
    items: List[Expression]

@dataclass
class FunctionCall(ASTNode):
    function: str
    args: List[Expression]


@dataclass
class ElementAccess(ASTNode):
    target: Identifier
    index: Expression


@dataclass
class DeleteElement(ASTNode):
    target: Identifier
    index: Expression


@dataclass
class ConditionalExpression(ASTNode):
    condition: Expression
    then_expr: Expression
    else_expr: Expression


# --- Statements ---


@dataclass
class Assignment(ASTNode):
    """Base class for different types of assignments."""

    pass


@dataclass
class LiteralAssignment(Assignment):
    target: Identifier
    value: Union[NumberLiteral, StringLiteral, BooleanLiteral, VectorLiteral]


@dataclass
class ExecutionAssignment(Assignment):
    target: Identifier
    expression: Union[FunctionCall, Identifier, ElementAccess, DeleteElement]


@dataclass
class ConditionalAssignment(Assignment):
    target: Identifier
    expression: ConditionalExpression


@dataclass
class MultiAssignment(Assignment):
    targets: List[Identifier]
    expression: FunctionCall


@dataclass
class ReturnStatement(ASTNode):
    values: List[Expression]


# --- Top-level Structures ---


@dataclass
class Directive(ASTNode):
    name: str
    value: Union[bool, Expression]


@dataclass
class Import(ASTNode):
    path: str


@dataclass
class Parameter(ASTNode):
    name: Identifier
    param_type: Identifier


@dataclass
class FunctionDefinition(ASTNode):
    name: Identifier
    params: List[Parameter]
    return_type: Union[Identifier, List[Identifier]]
    body: List[Union[Assignment, ReturnStatement]]
    docstring: Optional[str] = None


@dataclass
class Root(ASTNode):
    """The root of the entire AST, representing a single script file."""

    file_path: str
    imports: List[Import]
    directives: List[Directive]
    execution_steps: List[Assignment]
    function_definitions: List[FunctionDefinition]


# A generic type hint for any node in the AST
Node = Union[ASTNode, Root]
