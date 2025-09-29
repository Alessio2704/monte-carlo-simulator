"""
Custom exception types for the ValuaScript compiler.
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from vsc.parser.core.classes import Span


class ErrorCode(Enum):

    # --- Structural & Directive Errors ---
    MISSING_ITERATIONS_DIRECTIVE = "The @iterations directive is mandatory (e.g., '@iterations = 10000')."
    MISSING_OUTPUT_DIRECTIVE = "The @output directive is mandatory (e.g., '@output = final_result')."

    UNKNOWN_DIRECTIVE = "Unknown directive '@{name}'."
    DUPLICATE_DIRECTIVE = "The directive '@{name}' is defined more than once."
    INVALID_DIRECTIVE_VALUE = "{error_msg}"
    DIRECTIVE_NOT_ALLOWED_IN_MODULE = "The @{name} directive is not allowed when @module is declared."
    MODULE_DIRECTIVE_WITH_VALUE = "The @module directive does not accept a value. It should be used as '@module'."
    MODULE_DIRECTIVE_DECLARED_MORE_THAN_ONCE = "The @module directive must appear exactly once per file."
    OPERATOR_TYPE_MISMATCH = "The '{op}' operator cannot be used with a non-numeric type '{provided_type}'."

    # --- Module-Specific Errors ---
    GLOBAL_LET_IN_MODULE = "Global 'let' statements are not allowed in a module file. Only function definitions are permitted."

    # --- Variable & Definition Errors ---
    UNDEFINED_VARIABLE = "Variable '{name}' used in {context} is not defined."
    UNDEFINED_VARIABLE_IN_FUNC = "Variable '{name}' used in function '{func_name}' is not defined."
    DUPLICATE_VARIABLE = "Variable '{name}' is defined more than once."
    DUPLICATE_VARIABLE_IN_FUNC = "Variable '{name}' is defined more than once in function '{func_name}'."
    DUPLICATE_FUNCTION = "Function '{name}' is defined more than once."
    REDEFINE_BUILTIN_FUNCTION = "Cannot redefine built-in function '{name}'."
    FUNCTION_NAME_COLLISION = "Function '{name}' from '{path}' conflicts with another function of the same name."
    MIXED_TYPES_IN_VECTOR = "Vector literals cannot contain mixed types. Found types: {found_types}."
    ASSIGNMENT_ERROR = "Assignment error. The right side of assignment has {lhs_count} variables while the right side returns {rhs_count}"

    # --- Function Call & Type Errors ---
    UNKNOWN_FUNCTION = "Unknown function '{name}'."
    ARGUMENT_COUNT_MISMATCH = "Function '{name}' expects {expected} argument(s), but got {provided}."
    ARGUMENT_TYPE_MISMATCH = "Argument {arg_num} for '{name}' expects a '{expected}', but got a '{provided}'."
    RETURN_TYPE_MISMATCH = "Function '{name}' returns type '{provided}' but is defined to return '{expected}'."
    MISSING_RETURN_STATEMENT = "Function '{name}' is missing a return statement."
    INVALID_ITEM_IN_VECTOR = "Invalid item {value} in vector literal for '{name}'."
    INVALID_ITEM_TYPE_IN_VECTOR = "Invalid item type '{type}' found in vector literal."
    IF_CONDITION_NOT_BOOLEAN = "The condition for an 'if' expression must be a boolean (true/false) value, but got a '{provided}'."
    IF_ELSE_TYPE_MISMATCH = "The 'then' and 'else' branches of an 'if' expression must return the same type. The 'then' branch has type '{then_type}' but the 'else' branch has type '{else_type}'."
    LOGICAL_OPERATOR_TYPE_MISMATCH = "The '{op}' operator can only be used with boolean values, but got a '{provided}'."
    COMPARISON_TYPE_MISMATCH = "The '{op}' operator cannot be used to compare a '{left_type}' and a '{right_type}'."

    # --- Recursion Errors ---
    RECURSIVE_CALL_DETECTED = "Recursive function call detected: {path}"

    # --- Syntax Pre-Parsing Errors ---
    SYNTAX_MISSING_VALUE_AFTER_EQUALS = "Syntax Error: Missing value after '='."
    SYNTAX_INCOMPLETE_ASSIGNMENT = "Syntax Error: Incomplete assignment."
    SYNTAX_UNMATCHED_BRACKET = "Syntax Error: Unmatched closing bracket '{char} was never closed."
    SYNTAX_UNCLOSED_STRING = "Syntax Error: Unclosed string literal"
    SYNTAX_RESERVED_KEYWORD_AS_IDENTIFIER = "Syntax Error: Cannot use reserved keyword '{ident}' as a variable name."
    SYNTAX_INVALID_IDENTIFIER = "Syntax Error: {ident}' is not a valid identifier name."

    # This code is for when the parser finds a token that is valid, but not in the right place.
    # The 'details' will be dynamically generated (e.g., "Expected a number but found 'xyz'").
    SYNTAX_UNEXPECTED_TOKEN = "Syntax Error: Invalid syntax. {details}"

    # This code is for when the lexer finds a character that doesn't belong to any token.
    SYNTAX_INVALID_CHARACTER = "Syntax Error: Invalid character '{char}' found."

    # This is a fallback for any other, less common parsing errors from Lark.
    SYNTAX_PARSING_ERROR = "Syntax Error: A general parsing error occurred. Details: {details}"

    # --- Import Errors ---
    IMPORT_FILE_NOT_FOUND = "Imported file not found: '{path}'"
    IMPORT_NOT_A_MODULE = "Imported file '{path}' is not a valid module. It must contain the @module directive."
    CIRCULAR_IMPORT = "Circular import detected. The file '{path}' is already part of the import chain."
    CANNOT_IMPORT_FROM_STDIN = "@import is not supported when reading from stdin because file paths cannot be resolved."


class ValuaScriptError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        span: Optional["Span"] = None,
        file_path: Optional[str] = None,
        **kwargs,
    ):
        self.code = code
        self.span = span
        self.details = kwargs

        # --- 1. Generate the core error message ---
        # The format string (e.g., "Unknown directive '@{name}'") is populated
        # with any extra data it needs from kwargs.
        core_message = code.value.format(**kwargs)

        # --- 2. Determine the location prefix ---
        location_prefix = ""
        # The best case: we have a span with all details.
        if span:
            # The span's file_path is the most reliable source.
            location_prefix = f"Error in '{span.file_path}' (Line: {span.s_line}, Column: {span.s_col}):\n"
        # Fallback: we only have a file path for a global error.
        elif file_path:
            location_prefix = f"Error in '{file_path}': "
        # Worst case: we have no location info.

        # --- 3. Combine them for the final message ---
        self.message = location_prefix + core_message

        super().__init__(self.message)


# InternalCompilerError remains unchanged
class InternalCompilerError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
