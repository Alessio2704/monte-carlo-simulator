import os
from lark import Lark, Transformer, Token, LarkError
from textwrap import dedent
from ..config.config import MATH_OPERATOR_MAP, COMPARISON_OPERATOR_MAP, LOGICAL_OPERATOR_MAP
from .helpers import pre_parsing_checks, _translate_lark_error
from .classes import *

LARK_PARSER = None

try:
    # Use importlib.resources for robust package data access
    from importlib.resources import files as pkg_files

    # The path is relative to the 'vsc.parser' subpackage
    valuascript_grammar = (pkg_files("vsc.parser") / "valuascript.lark").read_text()

    # Note here the start="start" parameter must match the
    # "start" directive in the .lark file
    # as said there it is not mandatory but it is highly recommended
    LARK_PARSER = Lark(valuascript_grammar, start="start", parser="earley")
except Exception:
    # Fallback for development environments or older Python versions
    grammar_path = os.path.join(os.path.dirname(__file__), "valuascript.lark")
    with open(grammar_path, "r") as f:
        valuascript_grammar = f.read()
    LARK_PARSER = Lark(valuascript_grammar, start="start", parser="earley")


class ValuaScriptTransformer(Transformer):
    """
    Transforms the Lark parse tree into a more structured dataclass format (a high-level AST).
    The way this works is straightforward: each function declared inside this class is called
    whenever the Lark Parser encounters a "rule" or an alias with the same name; the transformation
    starts from the bottom (atoms) and works backwards.
    There are also "pass-through" functions to handle inlined operators: we simply unbox the value
    returning the first element (i.e. return items[0]).
    The resulting representation is easier to work with in subsequent compilation stages.
    """
        
    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__()

    # --- Helper methods for creating spans ---
    def _create_span_from_token(self, token: Token) -> Span:
        """Creates a Span object from a single Lark Token."""
        return Span(token.line, token.column, token.end_line, token.end_column)

    def _get_span_from_items(self, items: list) -> Span:
        """Calculates a Span that covers a list of tokens and/or ASTNodes."""
        first = next((item for item in items if hasattr(item, "span") or isinstance(item, Token)), None)
        last = next((item for item in reversed(items) if hasattr(item, "span") or isinstance(item, Token)), first)

        if not first:  # Handle empty lists
            return Span(1, 1, 1, 1)

        s_line = first.span.s_line if hasattr(first, "span") else first.line
        s_col = first.span.s_col if hasattr(first, "span") else first.column
        e_line = last.span.e_line if hasattr(last, "span") else last.end_line
        e_col = last.span.e_col if hasattr(last, "span") else last.end_column

        return Span(s_line, s_col, e_line, e_col)

    def _build_infix_tree(self, items, operator_map):
        """Helper to build a left-associative tree for any infix expression."""
        if len(items) == 1:
            return items[0]

        tree, i = items[0], 1
        while i < len(items):
            op, right = items[i], items[i + 1]
            func_name = operator_map[op.value]
            span = Span(tree.span.s_line, tree.span.s_col, right.span.e_line, right.span.e_col)

            # Special handling for variadic functions (add, multiply, and, or)
            if isinstance(tree, FunctionCall) and tree.function == func_name and func_name in ("add", "multiply", "__and__", "__or__"):
                tree.args.append(right)
                tree.span = span  # Extend the span
            else:
                tree = FunctionCall(function=func_name, args=[tree, right], span=span)
            i += 2
        return tree

    # --- Terminal Transformations ---
    def STRING(self, s: Token):
        return StringLiteral(value=s.value[1:-1], span=self._create_span_from_token(s))

    def DOCSTRING(self, s: Token):
        content = s.value[3:-3]
        return dedent(content).strip()

    def TRUE(self, t: Token):
        return BooleanLiteral(value=True, span=self._create_span_from_token(t))

    def FALSE(self, f: Token):
        return BooleanLiteral(value=False, span=self._create_span_from_token(f))

    def SIGNED_NUMBER(self, n: Token):
        val = n.value.replace("_", "")
        num = float(val) if "." in val or "e" in val.lower() else int(val)
        return NumberLiteral(value=num, span=self._create_span_from_token(n))

    def CNAME(self, c: Token):
        return Identifier(name=c.value, span=self._create_span_from_token(c))

    # --- Rule Transformations ---
    def math_expression(self, items):
        return self._build_infix_tree(items, MATH_OPERATOR_MAP)

    def logical_and_expression(self, items):
        return self._build_infix_tree(items, LOGICAL_OPERATOR_MAP)

    def logical_or_expression(self, items):
        return self._build_infix_tree(items, LOGICAL_OPERATOR_MAP)

    def not_expression(self, items):
        if len(items) > 1 and isinstance(items[0], Token) and items[0].type == "NOT":
            return FunctionCall(function="__not__", args=[items[1]], span=self._get_span_from_items(items))
        return items[0]

    def comparison_expression(self, items):
        if len(items) > 1:
            return self._build_infix_tree(items, COMPARISON_OPERATOR_MAP)
        return items[0]

    def conditional_expression(self, items):
        if len(items) == 1:
            return items[0]
        return ConditionalExpression(condition=items[1], then_expr=items[3], else_expr=items[5], span=self._get_span_from_items(items))

    # Pass-through methods for inlined grammar rules
    def expression(self, i):
        return i[0]

    def or_expression(self, i):
        return i[0]

    def and_expression(self, i):
        return i[0]

    def add_expression(self, i):
        return i[0]

    def mul_expression(self, i):
        return i[0]

    def power(self, i):
        return i[0]

    def atom(self, i):
        return i[0]

    def arg(self, i):
        return i[0]

    def directive(self, i):
        return i[0]

    def boolean(self, i):
        return i[0]

    def multi_assignment_vars(self, items):
        return items

    def tuple_type(self, items):
        return items

    def tuple_expression(self, items):
        return items

    def return_statement(self, items):
        span = self._get_span_from_items(items)
        return_value = items[-1]
        values = return_value if isinstance(return_value, list) else [return_value]
        return ReturnStatement(values=values, span=span)

    def function_call(self, items):
        func_name_ident = items[0]
        args = [item for item in items[1:] if item is not None]
        return FunctionCall(function=func_name_ident.name, args=args, span=self._get_span_from_items(items))

    def vector(self, items):
        vector_items = [item for item in items[1:-1] if item is not None]
        return VectorLiteral(items=vector_items, span=self._get_span_from_items(items))

    def element_access(self, items):
        var_ident, index_expression = items
        return ElementAccess(target=var_ident, index=index_expression, span=self._get_span_from_items(items))

    def delete_element_vector(self, items):
        var_ident, end_expression = items
        return DeleteElement(target=var_ident, index=end_expression, span=self._get_span_from_items(items))

    def directive_setting(self, items):
        name_ident, value = items
        return Directive(name=name_ident.name, value=value, span=self._get_span_from_items(items))

    def valueless_directive(self, items):
        name_ident = items[0]
        return Directive(name=name_ident.name, value=BooleanLiteral(True, name_ident.span), span=name_ident.span)

    def import_directive(self, items):
        _, path_literal = items
        return Import(path=path_literal.value, span=self._get_span_from_items(items))

    def assignment(self, items):
        _let_token, var_items, expression = items
        span = self._get_span_from_items(items)

        if isinstance(var_items, list):  # Multi-assignment
            return MultiAssignment(targets=var_items, expression=expression, span=span)

        target_ident = var_items
        if isinstance(expression, (NumberLiteral, StringLiteral, BooleanLiteral, VectorLiteral)):
            return LiteralAssignment(target=target_ident, value=expression, span=span)
        if isinstance(expression, ConditionalExpression):
            return ConditionalAssignment(target=target_ident, expression=expression, span=span)

        # All other cases are execution assignments
        return ExecutionAssignment(target=target_ident, expression=expression, span=span)

    def function_body(self, items):
        return items

    def function_def(self, items):
        func_name_ident = items[0]
        body_list = items[-1]
        docstring = items[-2] if isinstance(items[-2], str) else None
        return_type_token = items[-3]
        params = [p for p in items[1:-3] if isinstance(p, Parameter)]
        span = self._get_span_from_items(items)

        if isinstance(return_type_token, list):
            processed_return_type = return_type_token
        else:
            processed_return_type = return_type_token

        return FunctionDefinition(
            name=func_name_ident,
            params=params,
            return_type=processed_return_type,
            body=body_list,
            docstring=docstring,
            span=span,
        )

    def param(self, items):
        name_ident, type_ident = items
        return Parameter(name=name_ident, param_type=type_ident, span=self._get_span_from_items(items))

    def start(self, children):
        span = self._get_span_from_items(children)
        safe_children = [c for c in children if c]

        return Root(
            file_path=self.file_path,
            imports=[i for i in safe_children if isinstance(i, Import)],
            directives=[i for i in safe_children if isinstance(i, Directive)],
            execution_steps=[i for i in safe_children if isinstance(i, Assignment)],
            function_definitions=[i for i in safe_children if isinstance(i, FunctionDefinition)],
            span=span,
        )


def parse_valuascript(script_content: str, file_path: str = "<stdin>") -> Root:
    """Parses the script content and transforms it into a high-level AST."""

    pre_parsing_checks(script_content)

    try:
        parse_tree = LARK_PARSER.parse(script_content)
        return ValuaScriptTransformer(file_path=file_path).transform(parse_tree)
    except LarkError as e:
        raise _translate_lark_error(e) from e
