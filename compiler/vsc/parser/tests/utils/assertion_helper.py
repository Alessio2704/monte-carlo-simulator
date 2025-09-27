from dataclasses import is_dataclass, fields

def assert_asts_equal(actual, expected):
    """
    Recursively asserts that two AST nodes are equal, ignoring the 'span' attribute.
    Provides detailed error messages for mismatches.
    """
    # First, check if the types are the same
    assert type(actual) == type(expected), \
        f"AST node types differ. Actual: {type(actual).__name__}, Expected: {type(expected).__name__}"

    if is_dataclass(actual):
        # It's a dataclass, compare all fields except 'span'
        for field in fields(actual):
            if field.name == 'span':
                continue  # The magic step: we skip the span comparison

            actual_value = getattr(actual, field.name)
            expected_value = getattr(expected, field.name)
            
            # Recursively call the assertion for the field's value
            assert_asts_equal(actual_value, expected_value)

    elif isinstance(actual, list):
        # It's a list, compare each item recursively
        assert len(actual) == len(expected), \
            f"List lengths differ. Actual: {len(actual)}, Expected: {len(expected)}"
        for act, exp in zip(actual, expected):
            assert_asts_equal(act, exp)
            
    else:
        # It's a primitive type (int, str, bool, None), do a direct comparison
        assert actual == expected, \
            f"Primitive values differ. Actual: '{actual}', Expected: '{expected}'"