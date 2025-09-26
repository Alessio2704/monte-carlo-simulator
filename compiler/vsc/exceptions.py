"""
Custom exception types for the ValuaScript compiler.
"""

from enum import Enum


class ErrorCode(Enum):

    # --- Structural & Directive Errors ---
    MISSING_ITERATIONS_DIRECTIVE = "In file '{file_path}': The @iterations directive is mandatory (e.g., '@iterations = 10000')."
    MISSING_OUTPUT_DIRECTIVE = "In file '{file_path}': The @output directive is mandatory (e.g., '@output = final_result')."

    UNKNOWN_DIRECTIVE = "L{line}: Unknown directive '@{name}'."
    DUPLICATE_DIRECTIVE = "L{line}: The directive '@{name}' is defined more than once."
    INVALID_DIRECTIVE_VALUE = "L{line}: {error_msg}"
    DIRECTIVE_NOT_ALLOWED_IN_MODULE = "L{line}: The @{name} directive is not allowed when @module is declared."
    MODULE_WITH_VALUE = "L{line}: The @module directive does not accept a value. It should be used as '@module'."
    OPERATOR_TYPE_MISMATCH = "L{line}: The '{op}' operator cannot be used with a non-numeric type '{provided_type}'."

    # --- Module-Specific Errors ---
    GLOBAL_LET_IN_MODULE = "L{line}: Global 'let' statements are not allowed in a module file. Only function definitions are permitted."

    # --- Variable & Definition Errors ---
    UNDEFINED_VARIABLE = "L{line}: Variable '{name}' used in {context} is not defined."
    UNDEFINED_VARIABLE_IN_FUNC = "L{line}: Variable '{name}' used in function '{func_name}' is not defined."
    DUPLICATE_VARIABLE = "L{line}: Variable '{name}' is defined more than once."
    DUPLICATE_VARIABLE_IN_FUNC = "L{line}: Variable '{name}' is defined more than once in function '{func_name}'."
    DUPLICATE_FUNCTION = "L{line}: Function '{name}' is defined more than once."
    REDEFINE_BUILTIN_FUNCTION = "L{line}: Cannot redefine built-in function '{name}'."
    FUNCTION_NAME_COLLISION = "L{line}: Function '{name}' from '{path}' conflicts with another function of the same name."
    MIXED_TYPES_IN_VECTOR = "L{line}: Vector literals cannot contain mixed types. Found types: {found_types}."
    ASSIGNMENT_ERROR = "L{line}: Assignment error. The right side of assignment has {lhs_count} variables while the right side returns {rhs_count}"

    # --- Function Call & Type Errors ---
    UNKNOWN_FUNCTION = "L{line}: Unknown function '{name}'."
    ARGUMENT_COUNT_MISMATCH = "L{line}: Function '{name}' expects {expected} argument(s), but got {provided}."
    ARGUMENT_TYPE_MISMATCH = "L{line}: Argument {arg_num} for '{name}' expects a '{expected}', but got a '{provided}'."
    RETURN_TYPE_MISMATCH = "L{line}: Function '{name}' returns type '{provided}' but is defined to return '{expected}'."
    MISSING_RETURN_STATEMENT = "L{line}: Function '{name}' is missing a return statement."
    INVALID_ITEM_IN_VECTOR = "L{line}: Invalid item {value} in vector literal for '{name}'."
    INVALID_ITEM_TYPE_IN_VECTOR = "L{line}: Invalid item type '{type}' found in vector literal."
    IF_CONDITION_NOT_BOOLEAN = "L{line}: The condition for an 'if' expression must be a boolean (true/false) value, but got a '{provided}'."
    IF_ELSE_TYPE_MISMATCH = (
        "L{line}: The 'then' and 'else' branches of an 'if' expression must return the same type. The 'then' branch has type '{then_type}' but the 'else' branch has type '{else_type}'."
    )
    LOGICAL_OPERATOR_TYPE_MISMATCH = "L{line}: The '{op}' operator can only be used with boolean values, but got a '{provided}'."
    COMPARISON_TYPE_MISMATCH = "L{line}: The '{op}' operator cannot be used to compare a '{left_type}' and a '{right_type}'."

    # --- Recursion Errors ---
    RECURSIVE_CALL_DETECTED = "Recursive function call detected: {path}"

    # --- Syntax Pre-Parsing Errors ---
    SYNTAX_MISSING_VALUE_AFTER_EQUALS = "L{line}: Syntax Error: Missing value after '='."
    SYNTAX_INCOMPLETE_ASSIGNMENT = "L{line}: Syntax Error: Incomplete assignment."
    SYNTAX_UNMATCHED_BRACKET = "L{line}: Syntax Error: Unmatched closing bracket '{char} was never closed."
    SYNTAX_UNCLOSED_STRING = "L{line}: Syntax Error: Unclosed string literal"
    SYNTAX_RESERVED_KEYWORD_AS_IDENTIFIER = "L{line}: Syntax Error: Cannot use reserved keyword '{ident}' as a variable name."
    SYNTAX_INVALID_IDENTIFIER = "L{line}: Syntax Error: {ident}' is not a valid identifier name."

    # --- Import Errors ---
    IMPORT_FILE_NOT_FOUND = "L{line}: Imported file not found: '{path}'"
    IMPORT_NOT_A_MODULE = "L{line}: Imported file '{path}' is not a valid module. It must contain the @module directive."
    CIRCULAR_IMPORT = "L{line}: Circular import detected. The file '{path}' is already part of the import chain."
    CANNOT_IMPORT_FROM_STDIN = "L{line}: @import is not supported when reading from stdin because file paths cannot be resolved."


class ValuaScriptError(Exception):
    """Custom exception for semantic or validation errors in a ValuaScript file."""

    def __init__(self, code: ErrorCode, line: int = -1, **kwargs):
        self.code = code
        self.line = line
        self.details = kwargs
        self.message = code.value.format(line=line, **kwargs)
        super().__init__(self.message)

    def __str__(self):
        return self.message


class InternalCompilerError(Exception):
    """
    Custom exception for bugs within the compiler itself.
    This ensures that multi-line error messages are formatted correctly by test runners.
    """

    def __init__(self, message: str):
        super().__init__(message)
