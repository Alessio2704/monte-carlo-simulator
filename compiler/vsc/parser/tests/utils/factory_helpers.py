from typing import List, Optional, Union

from vsc.parser.classes import *


def get_span(s_line: int = 1, s_col: int = 1, e_line: int = 1, e_col: int = 1, file_path: str | None = None):
    return Span(s_line=s_line, s_col=s_col, e_line=e_line, e_col=e_col)


def get_identifier(value: str):
    return Identifier(span=get_span(), value=value)


def get_number_literal(value: int | float):
    return NumberLiteral(span=get_span(), value=value)


def get_vector_literal(items: List[Node]):
    return VectorLiteral(span=get_span(), items=items)


def get_string_literal(value: str):
    return StringLiteral(span=get_span(), value=value)


def get_boolean_literal(value: bool):
    return BooleanLiteral(span=get_span(), value=value)


def get_tuple_literal(items: List[Expression]):
    return TupleLiteral(span=get_span(), items=items)


def get_param(name: str, param_type: str):
    return Parameter(span=get_span(), name=get_identifier(name), param_type=get_identifier(param_type))


def get_literal_assignment(target: str, value: NumberLiteral | StringLiteral | BooleanLiteral | VectorLiteral):
    return LiteralAssignment(span=get_span(), target=get_identifier(value=target), value=value)


def get_function_call(function: str, args: List[Expression]):
    return FunctionCall(span=get_span(), function=function, args=args)


def get_element_access(target: str, index: Expression):
    return ElementAccess(span=get_span(), target=get_identifier(target), index=index)


def get_delete_element(target: str, index: Expression):
    return DeleteElement(span=get_span(), target=get_identifier(target), index=index)


def get_execution_assignment(target: str, expression: FunctionCall | Identifier | ElementAccess | DeleteElement):
    return ExecutionAssignment(span=get_span(), target=get_identifier(target), expression=expression)


def get_multi_assignment(targets: List[Identifier], expression: FunctionCall):
    return MultiAssignment(span=get_span(), targets=targets, expression=expression)


def get_conditional_expression(condition: Expression, then_expr: Expression, else_expr: Expression):
    return ConditionalExpression(span=get_span(), condition=condition, then_expr=then_expr, else_expr=else_expr)


def get_conditional_assignment(target: str, condition: Expression, then_expr: Expression, else_expr: Expression):
    return ConditionalAssignment(span=get_span(), target=get_identifier(target), expression=get_conditional_expression(condition=condition, then_expr=then_expr, else_expr=else_expr))


def get_return_statement(returns: Expression):
    return ReturnStatement(get_span(), returns=returns)


def get_function_def(
    name: str, params: Optional[List[tuple]] = None, return_type: Union[str, List[str]] = "scalar", body: Optional[List[Union[Assignment, ReturnStatement]]] = None, docstring: Optional[str] = None
) -> FunctionDefinition:
    """
    A flexible factory to build FunctionDefinition nodes for tests.

    Args:
        name: The name of the function.
        params: A list of (name, type) tuples, e.g., [("a", "scalar")]. Defaults to [].
        return_type: A string for a single type or a list of strings for a tuple type.
                     Defaults to "scalar".
        body: A list of statement nodes for the function body.
              Defaults to a simple `return 1`.
        docstring: An optional docstring.
    """
    # 1. Provide sensible defaults for optional arguments
    if params is None:
        param_objects = []
    else:
        param_objects = [get_param(name=p_name, param_type=p_type) for p_name, p_type in params]

    if body is None:
        # A great default: a simple function that just returns 1.
        body_nodes = [get_return_statement(returns=[get_number_literal(1)])]
    else:
        body_nodes = body

    # 2. Handle the return type being a single string or a list of strings
    if isinstance(return_type, str):
        return_type_node = get_identifier(return_type)
    else:  # It's a list for a tuple return
        return_type_node = [get_identifier(rt) for rt in return_type]

    # 3. Construct and return the final dataclass object
    return FunctionDefinition(name=get_identifier(name), params=param_objects, return_type=return_type_node, body=body_nodes, docstring=docstring, span=get_span())


def get_directive(name: str, value: Expression | bool):
    return Directive(span=get_span(), name=name, value=value)


def get_import(path: str):
    return Import(span=get_span(), path=path)


def get_import(path: str):
    return Import(span=get_span(), path=path)
