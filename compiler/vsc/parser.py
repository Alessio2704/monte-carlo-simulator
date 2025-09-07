import os
from lark import Lark, Transformer, Token
from textwrap import dedent
from .exceptions import ValuaScriptError

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
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'StringLiteral("{self.value}")'


class ValuaScriptTransformer(Transformer):
    """
    Transforms the Lark parse tree into a more structured dictionary format (a high-level AST).
    This representation is easier to work with in subsequent compilation stages.
    """

    def STRING(self, s):
        return _StringLiteral(s.value[1:-1])

    def DOCSTRING(self, s):
        # Remove the triple quotes and dedent the string
        content = s.value[3:-3]
        return dedent(content).strip()

    def infix_expression(self, items):
        # This flattens chained operations like `a + b + c` into a single function call
        # e.g., {"function": "add", "args": [a, b, c]}
        from .config import OPERATOR_MAP

        if len(items) == 1:
            return items[0]
        tree, i = items[0], 1
        while i < len(items):
            op, right = items[i], items[i + 1]
            func_name = OPERATOR_MAP[op.value]
            if isinstance(tree, dict) and tree.get("function") == func_name and func_name in ("add", "multiply"):
                tree["args"].append(right)
            else:
                tree = {"function": func_name, "args": [tree, right]}
            i += 2
        return tree

    # --- Pass-through rules to simplify the tree ---
    def expression(self, i):
        return i[0]

    def term(self, i):
        return i[0]

    def factor(self, i):
        return i[0]

    def power(self, i):
        return i[0]

    def atom(self, i):
        return i[0]

    def arg(self, i):
        return i[0]
        
    def directive(self, items):
        return items[0]

    # --- Terminal transformations ---
    def SIGNED_NUMBER(self, n):
        val = n.value.replace("_", "")
        return float(val) if "." in val or "e" in val.lower() else int(val)

    def CNAME(self, c):
        return c

    # --- Rule transformations ---
    def function_call(self, items):
        func_name_token = items[0]
        args = [item for item in items[1:] if item is not None]
        return {"function": str(func_name_token), "args": args}

    def vector(self, items):
        return [item for item in items if item is not None]

    def element_access(self, items):
        var_token, index_expression = items
        return {"function": "get_element", "args": [var_token, index_expression]}

    def delete_element_vector(self, items):
        var_token, end_expression = items
        return {"function": "delete_element", "args": [var_token, end_expression]}

    def directive_setting(self, items):
        return {"type": "directive", "name": str(items[0]), "value": items[1], "line": items[0].line}

    def valueless_directive(self, items):
        # This handles directives like @module that don't have a value.
        # We assign `True` as the value for consistency.
        directive_token = items[0]
        return {"type": "directive", "name": str(directive_token), "value": True, "line": directive_token.line}

    def assignment(self, items):
        _let_token, var_token, expression = items
        base_step = {"result": str(var_token), "line": var_token.line}
        if isinstance(expression, dict):
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

        return {
            "type": "function_definition",
            "name": str(func_name_token),
            "params": [p for p in params if isinstance(p, dict)],
            "return_type": str(return_type_token),
            "body": body_list,
            "docstring": docstring,
            "line": func_name_token.line,
        }

    def param(self, items):
        return {"name": str(items[0]), "type": str(items[1])}

    def return_statement(self, items):
        return {"type": "return_statement", "value": items[0]}

    def start(self, children):
        return {
            "directives": [i for i in children if i.get("type") == "directive"],
            "execution_steps": [i for i in children if i.get("type") in ("execution_assignment", "literal_assignment")],
            "function_definitions": [i for i in children if i.get("type") == "function_definition"],
        }


def parse_valuascript(script_content: str):
    """Parses the script content and transforms it into a high-level AST."""
    # --- PRE-PARSING CHECKS for better error messages ---
    for i, line in enumerate(script_content.splitlines()):
        clean_line = line.split("#", 1)[0].strip()
        if not clean_line:
            continue
        if clean_line.count("(") != clean_line.count(")"):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Unmatched opening parenthesis.")
        if clean_line.count("[") != clean_line.count("]"):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Unmatched opening bracket.")
        if (clean_line.startswith("let") or clean_line.startswith("@")) and clean_line.endswith("="):
            raise ValuaScriptError(f"L{i+1}: Syntax Error: Missing value after '='.")
        if clean_line.startswith("let") and "=" not in clean_line:
            if len(clean_line.split()) > 0 and clean_line.split()[0] == "let":
                raise ValuaScriptError(f"L{i+1}: Syntax Error: Incomplete assignment.")

    parse_tree = LARK_PARSER.parse(script_content)
    return ValuaScriptTransformer().transform(parse_tree)