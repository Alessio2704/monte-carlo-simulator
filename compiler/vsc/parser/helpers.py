import re
from lark import Lark, Transformer, Token
from lark.exceptions import UnexpectedToken, UnexpectedCharacters, LarkError
from vsc.exceptions import ValuaScriptError, ErrorCode

# --- Constants for the checks ---
RESERVED_KEYWORDS = {"let", "if", "then", "else", "true", "false", "and", "or", "not", "func", "return"}
VALID_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}"}
OPENING_BRACKETS = set(BRACKET_PAIRS.keys())
CLOSING_BRACKETS = set(BRACKET_PAIRS.values())


def pre_parsing_checks(script_content: str):
    """
    Performs several simple pre-parsing checks for common errors to provide better error messages.
    This function checks for:
    1. Mismatched or unclosed brackets across the entire file.
    2. Use of reserved keywords as variable names.
    3. Invalid identifier formats.
    4. Incomplete assignments or directives (e.g., lines ending in '=').
    """

    # --- Check #1: Mismatched or Unclosed Brackets ---
    # This check scans the entire file, ignoring comments and content within strings
    # to accurately track the nesting of brackets, parentheses, and braces.
    bracket_stack = []  # A stack of (char, line_num)
    for i, line in enumerate(script_content.splitlines()):
        line_num = i + 1
        line_no_comment = line.split("#", 1)[0]
        in_string = False
        for char in line_no_comment:
            if char == '"':
                in_string = not in_string

            if in_string:
                continue

            if char in OPENING_BRACKETS:
                bracket_stack.append((char, line_num))
            elif char in CLOSING_BRACKETS:
                if not bracket_stack:
                    raise ValuaScriptError(ErrorCode.SYNTAX_UNMATCHED_BRACKET, line=line_num, char=char)

                opening_char, _ = bracket_stack.pop()
                if BRACKET_PAIRS[opening_char] != char:
                    # This error indicates a mismatch like `( ]`. The error code is generic,
                    # but it correctly identifies the location and offending character.
                    raise ValuaScriptError(ErrorCode.SYNTAX_UNMATCHED_BRACKET, line=line_num, char=char)

    if bracket_stack:
        # If the stack is not empty after checking the whole file, there's an unclosed bracket.
        opening_char, line_num = bracket_stack[-1]
        raise ValuaScriptError(ErrorCode.SYNTAX_UNMATCHED_BRACKET, line=line_num, char=opening_char)

    # --- Line-by-line checks ---
    for i, line in enumerate(script_content.splitlines()):
        line_num = i + 1
        clean_line = line.split("#", 1)[0].strip()

        if not clean_line:
            continue

        # --- Existing Checks: Missing value or incomplete assignment ---
        if (clean_line.startswith("let") or clean_line.startswith("@")) and clean_line.endswith("="):
            raise ValuaScriptError(ErrorCode.SYNTAX_MISSING_VALUE_AFTER_EQUALS, line=line_num)

        # --- Check #3 (Reserved Keywords) & #4 (Invalid Identifiers) ---
        if clean_line.startswith("let "):
            # This also handles the original "incomplete assignment" check in a more robust way.
            if "=" not in clean_line:
                if len(clean_line.split()) > 0 and clean_line.split()[0] == "let":
                    raise ValuaScriptError(ErrorCode.SYNTAX_INCOMPLETE_ASSIGNMENT, line=line_num)
                continue

            # Extract the part between 'let' and '=', which contains the variable names.
            vars_part = clean_line.split("=", 1)[0][3:].strip()

            # Handle multi-assignment by splitting by comma.
            identifiers_to_check = [v.strip() for v in vars_part.split(",")]

            for ident in identifiers_to_check:
                if not ident:  # Handles cases like `let a, = ...` or empty parts.
                    continue

                # Check #3: Cannot use a reserved keyword as a variable name.
                if ident in RESERVED_KEYWORDS:
                    raise ValuaScriptError(ErrorCode.SYNTAX_RESERVED_KEYWORD_AS_IDENTIFIER, line=line_num, ident=ident)

                # Check #4: Identifier must follow the language's format (e.g., C-style).
                if not VALID_IDENTIFIER_REGEX.match(ident):
                    raise ValuaScriptError(ErrorCode.SYNTAX_INVALID_IDENTIFIER, line=line_num, ident=ident)


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


def _translate_lark_error(err: LarkError) -> ValuaScriptError:
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
        found_str = f"but found '{found_token.value}' instead."
        if found_token.type == "$END":
            found_str = "but reached the end of the file instead."

        details = f"{expected_str}, {found_str}" if expected_str else f"Found unexpected token '{found_token.value}'."

        return ValuaScriptError(code=ErrorCode.SYNTAX_UNEXPECTED_TOKEN, line=err.line, details=details)

    elif isinstance(err, UnexpectedCharacters):
        return ValuaScriptError(code=ErrorCode.SYNTAX_INVALID_CHARACTER, line=err.line, char=err.char)

    # Fallback for any other Lark error
    return ValuaScriptError(code=ErrorCode.SYNTAX_PARSING_ERROR, line=getattr(err, "line", -1), details=str(err))
