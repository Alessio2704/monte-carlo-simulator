import os
from lark import Lark, Transformer, Token
from textwrap import dedent
from .exceptions import ValuaScriptError, ErrorCode
from .config import MATH_OPERATOR_MAP, COMPARISON_OPERATOR_MAP, LOGICAL_OPERATOR_MAP

LARK_PARSER = None

try:
    # Use importlib.resources for robust package data access
    from importlib.resources import files as pkg_files

    valuasc_grammar = (pkg_files("vsc") / "valuascript.lark").read_text()
    LARK_PARSER = Lark(valuasc_grammar, start="start", parser="earley")
except Exception:
    # Fallback for development environments or older Python versions
    grammar_path = os.path.join(os.path.dirname(__file__), "valuascript.lark")
    with open(grammar_path, "r") as f:
        valuasc_grammar = f.read()
    LARK_PARSER = Lark(valuasc_grammar, start="start", parser="earley")


# A simple wrapper class to distinguish parsed strings from variable names
class _StringLiteral:
    def __init__(self, value, line=-1):
        self.value = value
        self.line = line

    def __repr__(self):
        return f'StringLiteral("{self.value}")'

    def __eq__(self, other):
        """
        Custom equality check. This is critical for optimization passes
        that use deepcopy and value comparison to detect changes.
        """
        if not isinstance(other, _StringLiteral):
            return NotImplemented
        return self.value == other.value


class ValuaScriptTransformer(Transformer):
    """
    Transforms the Lark parse tree into a more structured dictionary format (a high-level AST).
    This representation is easier to work with in subsequent compilation stages.
    """

    def _build_infix_tree(self, items, operator_map):
        """Helper to build a left-associative tree for any infix expression."""
        if len(items) == 1:
            return items[0]
        tree, i = items[0], 1
        while i < len(items):
            op, right = items[i], items[i + 1]
            func_name = operator_map[op.value]
            # Special handling for variadic functions (add, multiply, and, or)
            if isinstance(tree, dict) and tree.get("function") == func_name and func_name in ("add", "multiply", "__and__", "__or__"):
                tree["args"].append(right)
            else:
                tree = {"function": func_name, "args": [tree, right]}
            i += 2
        return tree

    def STRING(self, s):
        return _StringLiteral(s.value[1:-1], s.line)

    def DOCSTRING(self, s):
        # Remove the triple quotes and dedent the string
        content = s.value[3:-3]
        return dedent(content).strip()

    def TRUE(self, _):
        return True

    def FALSE(self, _):
        return False

    def math_expression(self, items):
        return self._build_infix_tree(items, MATH_OPERATOR_MAP)

    def logical_and_expression(self, items):
        return self._build_infix_tree(items, LOGICAL_OPERATOR_MAP)

    def logical_or_expression(self, items):
        return self._build_infix_tree(items, LOGICAL_OPERATOR_MAP)

    def not_expression(self, items):
        if len(items) > 1 and isinstance(items[0], Token) and items[0].type == "NOT":
            return {"function": "__not__", "args": [items[1]]}
        else:
            return items[0]

    def comparison_expression(self, items):
        if len(items) > 1:
            return self._build_infix_tree(items, COMPARISON_OPERATOR_MAP)
        else:
            return items[0]

    def conditional_expression(self, items):
        if len(items) == 1:
            return items[0]
        return {"type": "conditional_expression", "condition": items[1], "then_expr": items[3], "else_expr": items[5]}

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

    def SIGNED_NUMBER(self, n):
        val = n.value.replace("_", "")
        return float(val) if "." in val or "e" in val.lower() else int(val)

    def CNAME(self, c):
        return c

    def multi_assignment_vars(self, items):
        return items

    def tuple_type(self, items):
        return items

    def tuple_expression(self, items):
        if len(items) == 1:
            return items[0]
        return {"_is_tuple_return": True, "values": items}

    def return_statement(self, items):
        line_num = items[0].line if hasattr(items[0], "line") else -1
        return_value = items[-1]  # The expression is always the last item
        if isinstance(return_value, dict) and return_value.get("_is_tuple_return"):
            return {"type": "return_statement", "values": return_value["values"], "line": line_num}
        return {"type": "return_statement", "value": return_value, "line": line_num}

    def function_call(self, items):
        func_name_token = items[0]
        args = [item for item in items[1:] if item is not None]
        return {"function": str(func_name_token), "args": args, "line": func_name_token.line}

    def vector(self, items):
        # The first item is now the LSQB token, which has the line number.
        lsqb_token = items[0]

        # The actual vector items are everything between the brackets.
        # We slice from the second item to the second-to-last item.
        vector_items = [item for item in items[1:-1] if item is not None]

        # Return the new structured dictionary including the line number.
        return {"_is_vector_literal": True, "items": vector_items, "line": lsqb_token.line}

    def element_access(self, items):
        var_token, index_expression = items
        return {"function": "GetElement", "args": [var_token, index_expression]}

    def delete_element_vector(self, items):
        var_token, end_expression = items
        return {"function": "DeleteElement", "args": [var_token, end_expression]}

    def directive_setting(self, items):
        return {"type": "directive", "name": str(items[0]), "value": items[1], "line": items[0].line}

    def valueless_directive(self, items):
        directive_token = items[0]
        return {"type": "directive", "name": str(directive_token), "value": True, "line": directive_token.line}

    def import_directive(self, items):
        import_token, path_literal = items
        return {"type": "import", "path": path_literal.value, "line": import_token.line}

    def assignment(self, items):
        _let_token, var_items, expression = items
        line_source = var_items[0] if isinstance(var_items, list) else var_items
        line = line_source.line

        if isinstance(var_items, list):
            results_as_strings = [str(v) for v in var_items]
            base_step = {"results": results_as_strings, "line": line, "type": "multi_assignment"}
            if isinstance(expression, dict) and "function" in expression:
                base_step.update(expression)
                return base_step
            return {"results": results_as_strings, "line": line, "type": "multi_assignment", "expression": expression}

        base_step = {"result": str(var_items), "line": line}

        if isinstance(expression, dict) and expression.get("type") == "conditional_expression":
            base_step.update(expression)
        elif isinstance(expression, dict) and expression.get("_is_vector_literal"):
            base_step.update({"type": "literal_assignment", "value": expression})
        elif isinstance(expression, dict):
            base_step.update({"type": "execution_assignment", **expression})
        elif isinstance(expression, Token):
            base_step.update({"type": "execution_assignment", "function": "identity", "args": [expression]})
        else:
            base_step.update({"type": "literal_assignment", "value": expression})
        return base_step

    def function_body(self, items):
        return items

    def function_def(self, items):
        func_name_token = items[0]
        body_list = items[-1]
        docstring = items[-2]
        return_type_token = items[-3]
        params = items[1:-3]

        if isinstance(return_type_token, list):
            processed_return_type = [str(t) for t in return_type_token]
        else:
            processed_return_type = str(return_type_token)

        return {
            "type": "function_definition",
            "name": str(func_name_token),
            "params": [p for p in params if isinstance(p, dict)],
            "return_type": processed_return_type,
            "body": body_list,
            "docstring": docstring,
            "line": func_name_token.line,
        }

    def param(self, items):
        return {"name": str(items[0]), "type": str(items[1])}

    def start(self, children):
        safe_children = [c for c in children if c]
        assignment_types = ("execution_assignment", "literal_assignment", "conditional_expression", "multi_assignment")
        return {
            "imports": [i for i in safe_children if i.get("type") == "import"],
            "directives": [i for i in safe_children if i.get("type") == "directive"],
            "execution_steps": [i for i in safe_children if i.get("type") in assignment_types],
            "function_definitions": [i for i in safe_children if i.get("type") == "function_definition"],
        }


def parse_valuascript(script_content: str):
    """Parses the script content and transforms it into a high-level AST."""
    for i, line in enumerate(script_content.splitlines()):
        clean_line = line.split("#", 1)[0].strip()
        if not clean_line:
            continue
        if (clean_line.startswith("let") or clean_line.startswith("@")) and clean_line.endswith("="):
            raise ValuaScriptError(ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS, line=i + 1)
        if clean_line.startswith("let") and "=" not in clean_line:
            if len(clean_line.split()) > 0 and clean_line.split()[0] == "let":
                raise ValuaScriptError(ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT, line=i + 1)

    parse_tree = LARK_PARSER.parse(script_content)
    return ValuaScriptTransformer().transform(parse_tree)
