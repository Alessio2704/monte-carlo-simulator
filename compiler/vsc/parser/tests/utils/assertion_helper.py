from pydantic import BaseModel
from vsc.parser.classes import ASTNode

def assert_asts_equal(actual, expected):
    """
    Recursively asserts that two AST nodes (Pydantic Models) are equal,
    ignoring the 'span' attribute. Provides detailed error messages for mismatches.
    """
    # First, check if the types are the same
    assert type(actual) == type(expected),  f"AST node types differ. Actual: {type(actual).__name__}, Expected: {type(expected).__name__}"

    # Check if the object is an instance of our ASTNode base class
    # or any Pydantic model. `isinstance(actual, BaseModel)` is a robust way.
    if isinstance(actual, BaseModel):
        # It's a Pydantic model, compare all fields except 'span'
        for field_name in type(actual).model_fields:
            if field_name == 'span':
                continue  # We skip the span comparison

            actual_value = getattr(actual, field_name)
            expected_value = getattr(expected, field_name)
            
            # Recursively call the assertion for the field's value
            try:
                assert_asts_equal(actual_value, expected_value)
            except AssertionError as e:
                # Re-raise the error with context about which field failed
                raise AssertionError(f"Mismatch in field '{field_name}' of {type(actual).__name__}:\n{e}") from e

    elif isinstance(actual, list):
        # It's a list, compare each item recursively
        assert len(actual) == len(expected), f"List lengths differ. Actual: {len(actual)}, Expected: {len(expected)}"
        for i, (act, exp) in enumerate(zip(actual, expected)):
            try:
                assert_asts_equal(act, exp)
            except AssertionError as e:
                raise AssertionError(f"Mismatch at index [{i}] of a list:\n{e}") from e
            
    else:
        # It's a primitive type (int, str, bool, None), do a direct comparison
        assert actual == expected, f"Primitive values differ. Actual: '{actual}', Expected: '{expected}'"