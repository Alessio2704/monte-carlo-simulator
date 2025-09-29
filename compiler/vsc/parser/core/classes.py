"""
Defines the formal data structures (contracts) for the Abstract Syntax Tree (AST)
produced by the parser stage.

Each node is represented by a dataclass and includes a `Span` object to track its
location in the source code, enabling precise error reporting in later stages.
"""

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# --- Core Data Structures ---


class Span(BaseModel):
    """Represents a location in the source code for precise error reporting."""

    s_line: int
    s_col: int
    e_line: int
    e_col: int
    file_path: Optional[str] = None


class ASTNode(BaseModel):
    """A base class for all AST nodes, ensuring they have a span."""

    span: Span


# --- Literals and Identifiers ---


class NumberLiteral(ASTNode):
    value: Union[int, float]


class StringLiteral(ASTNode):
    value: str


class BooleanLiteral(ASTNode):
    value: bool


class Identifier(ASTNode):
    value: str


class VectorLiteral(ASTNode):
    items: List["Expression"]  # Using 'Node' for flexible typing


# --- Expressions ---
# A generic type hint for any expression node
Expression = Union[NumberLiteral, StringLiteral, BooleanLiteral, Identifier, VectorLiteral, "TupleLiteral", "FunctionCall", "ElementAccess", "DeleteElement", "ConditionalExpression"]


class TupleLiteral(ASTNode):
    items: List[Expression]


class FunctionCall(ASTNode):
    function: str
    args: List[Expression]


class ElementAccess(ASTNode):
    target: Identifier
    index: Expression


class DeleteElement(ASTNode):
    target: Identifier
    index: Expression


class ConditionalExpression(ASTNode):
    condition: Expression
    then_expr: Expression
    else_expr: Expression


# --- Statements ---


class Assignment(ASTNode):
    """Base class for different types of assignments."""

    pass


class LiteralAssignment(Assignment):
    assignment_type: Literal["literal_assignment"] = "literal_assignment"
    target: Identifier
    value: Union[NumberLiteral, StringLiteral, BooleanLiteral, VectorLiteral]


class ExecutionAssignment(Assignment):
    assignment_type: Literal["execution_assignment"] = "execution_assignment"
    target: Identifier
    expression: Union[FunctionCall, ElementAccess, DeleteElement]


class ConditionalAssignment(Assignment):
    assignment_type: Literal["conditional_assignment"] = "conditional_assignment"
    target: Identifier
    expression: ConditionalExpression

class CopyAssignment(Assignment):
    assignment_type: Literal["copy_assignment"] = "copy_assignment"
    target: Identifier
    source: Identifier


class MultiAssignment(Assignment):
    assignment_type: Literal["multi_assignment"] = "multi_assignment"
    targets: List[Identifier]
    expression: FunctionCall


class MultiCopyAssignment(Assignment):
    assignment_type: Literal["multi_copy_assignment"] = "multi_copy_assignment"
    targets: List[Identifier]
    source: Union[Identifier, TupleLiteral]


AnyAssignment = Union[LiteralAssignment, ExecutionAssignment, ConditionalAssignment, CopyAssignment, MultiAssignment, MultiCopyAssignment]
DiscriminatedAssignment = Annotated[AnyAssignment, Field(discriminator="assignment_type")]


class ReturnStatement(ASTNode):
    returns: Expression

# --- Top-level Structures ---


class Directive(ASTNode):
    name: str
    value: Union[bool, Expression]


class Import(ASTNode):
    path: str


class Parameter(ASTNode):
    name: Identifier
    param_type: Identifier


class FunctionDefinition(ASTNode):
    name: Identifier
    params: List[Parameter]
    return_type: Union[Identifier, List[Identifier]]
    body: List[Union[DiscriminatedAssignment, ReturnStatement]]
    docstring: Optional[str] = None


class Root(ASTNode):
    """The root of the entire AST, representing a single script file."""

    file_path: str
    imports: List[Import]
    directives: List[Directive]
    execution_steps: List[DiscriminatedAssignment]
    function_definitions: List[FunctionDefinition]


# A generic type hint for any node in the AST
Node = Union[ASTNode, Root]
