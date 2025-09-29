import re

from lark import Lark, Token, Transformer
from lark.exceptions import LarkError, UnexpectedCharacters, UnexpectedToken

from vsc.exceptions import ErrorCode, ValuaScriptError
from vsc.parser.core.classes import Span

# --- Constants for the checks ---
RESERVED_KEYWORDS = {"let", "if", "then", "else", "true", "false", "and", "or", "not", "func", "return"}
VALID_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}
OPENING_BRACKETS = set(BRACKET_PAIRS.keys())
CLOSING_BRACKETS = set(BRACKET_PAIRS.values())


def pre_parsing_checks(script_content: str, file_path: str):
    """
    Performs several simple pre-parsing checks for common errors to provide better error messages.
    Constructs Span objects for standardized error reporting.
    """

    # --- Check #1: Mismatched or Unclosed Brackets ---
    bracket_stack = []  # A stack of (char, line_num, col_num)
    for i, line in enumerate(script_content.splitlines()):
        line_num = i + 1
        line_no_comment = line.split("#", 1)[0]
        in_string = False
        for col_idx, char in enumerate(line_no_comment):
            col_num = col_idx + 1
            if char == '"':
                in_string = not in_string

            if in_string:
                continue

            if char in OPENING_BRACKETS:
                bracket_stack.append((char, line_num, col_num))
            elif char in CLOSING_BRACKETS:
                if not bracket_stack:
                    span = Span(s_line=line_num, s_col=col_num, e_line=line_num, e_col=col_num + 1, file_path=file_path)
                    raise ValuaScriptError(code=ErrorCode.SYNTAX_UNMATCHED_BRACKET, span=span, char=char)

                opening_char, _, _ = bracket_stack.pop()
                if BRACKET_PAIRS[opening_char] != char:
                    span = Span(s_line=line_num, s_col=col_num, e_line=line_num, e_col=col_num + 1, file_path=file_path)
                    raise ValuaScriptError(code=ErrorCode.SYNTAX_UNMATCHED_BRACKET, span=span, char=char)

    if bracket_stack:
        opening_char, line_num, col_num = bracket_stack[-1]
        span = Span(s_line=line_num, s_col=col_num, e_line=line_num, e_col=col_num + 1, file_path=file_path)
        raise ValuaScriptError(code=ErrorCode.SYNTAX_UNMATCHED_BRACKET, span=span, char=opening_char)

    # --- Line-by-line checks ---
    for i, line in enumerate(script_content.splitlines()):
        line_num = i + 1
        clean_line = line.split("#", 1)[0].strip()

        if not clean_line:
            continue

        # For line-level errors, creating a span pointing to the start of the line is sufficient.
        line_start_span = Span(s_line=line_num, s_col=1, e_line=line_num, e_col=len(clean_line) or 1, file_path=file_path)

        if (clean_line.startswith("let") or clean_line.startswith("@")) and clean_line.endswith("="):
            raise ValuaScriptError(code=ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS, span=line_start_span)

        if clean_line.startswith("let"):
            if "=" not in clean_line:
                if len(clean_line.split()) > 0 and clean_line.split()[0] == "let":
                    raise ValuaScriptError(code=ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT, span=line_start_span)
                continue

            vars_part = clean_line.split("=", 1)[0][3:].strip()
            identifiers_to_check = [v.strip() for v in vars_part.split(",")]

            for ident in identifiers_to_check:
                if not ident:
                    continue

                if ident in RESERVED_KEYWORDS:
                    # We can even create a more precise span for the specific keyword
                    col = clean_line.find(ident) + 1
                    ident_span = Span(s_line=line_num, s_col=col, e_line=line_num, e_col=col + len(ident), file_path=file_path)
                    raise ValuaScriptError(code=ErrorCode.SYNTAX_RESERVED_KEYWORD_AS_IDENTIFIER, span=ident_span, ident=ident)

                if not VALID_IDENTIFIER_REGEX.match(ident):
                    col = clean_line.find(ident) + 1
                    ident_span = Span(s_line=line_num, s_col=col, e_line=line_num, e_col=col + len(ident), file_path=file_path)
                    raise ValuaScriptError(code=ErrorCode.SYNTAX_INVALID_IDENTIFIER, span=ident_span, ident=ident)


# A mapping from Lark's internal token names to friendly, human-readable names.
# You should expand this list with all the important tokens in your grammar.
FRIENDLY_TOKEN_NAMES = {
    "CNAME": "a variable or function name",
    "SIGNED_NUMBER": "a number",
    "STRING": "a string literal",
    "LET": "the 'let' keyword",
    "IF": "the 'if' keyword",
    "RSQB": "a closing bracket ']'",
    "LSQB": "an opening bracket '['",
    "RPAR": "a closing parenthesis ')'",
    "LPAR": "an opening parenthesis '('",
    "EQ": "an equals sign '='",
    "COMMA": "a comma ','",
    "$END": "the end of the file",  # Lark's token for the end of input
}


def _translate_lark_error(err: LarkError, file_path: str) -> ValuaScriptError:
    """Translates a generic LarkError into a user-friendly ValuaScriptError."""

    if isinstance(err, UnexpectedToken):
        # Build a helpful message about what was expected.
        expected_str = ""
        if err.expected:
            friendly_expected = [FRIENDLY_TOKEN_NAMES.get(e, e) for e in sorted(err.expected)]
            if len(friendly_expected) > 1:
                expected_str = f"Expected one of: {', '.join(friendly_expected[:-1])} or {friendly_expected[-1]}"
            elif friendly_expected:
                expected_str = f"Expected {friendly_expected[0]}"

        found_token = err.token
        span = Span(s_line=found_token.line, s_col=found_token.column, e_line=found_token.end_line, e_col=found_token.end_column, file_path=file_path)
        found_str = f"but found '{found_token.value}' instead."
        if found_token.type == "$END":
            found_str = "but reached the end of the file instead."

        details = f"{expected_str}, {found_str}" if expected_str else f"Found unexpected token '{found_token.value}'."

        return ValuaScriptError(code=ErrorCode.SYNTAX_UNEXPECTED_TOKEN, span=span, details=details)

    elif isinstance(err, UnexpectedCharacters):
        span = Span(s_line=err.line, s_col=err.column, e_line=err.line, e_col=err.column, file_path=file_path)
        return ValuaScriptError(code=ErrorCode.SYNTAX_INVALID_CHARACTER, span=span, char=err.char)

    # Fallback for any other Lark error
    return ValuaScriptError(code=ErrorCode.SYNTAX_PARSING_ERROR, line=getattr(err, "line", -1), details=str(err), file_path=file_path)
