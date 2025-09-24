import pkgutil
import importlib

# The master dictionary that will hold all test cases from all domains.
BUILTIN_TEST_CASES = {}

# Discover and import all modules in the current package (e.g., financial.py)
for _, name, _ in pkgutil.iter_modules(__path__):
    try:
        # Dynamically import the module (e.g., tests.end_to_end.builtin.cases.financial)
        module = importlib.import_module(f".{name}", __name__)

        if hasattr(module, "TEST_CASES"):
            # Check for duplicate test case names before merging
            for key in module.TEST_CASES:
                if key in BUILTIN_TEST_CASES:
                    # This is a developer error (e.g., defining a test for 'add' in two files)
                    raise NameError(f"Duplicate test case '{key}' defined in " f"'tests/end_to_end/builtin/cases/{name}.py'.")

            # Merge the test cases from the module into the master dictionary
            BUILTIN_TEST_CASES.update(module.TEST_CASES)

    except ImportError as e:
        print(f"Warning: Could not import test cases from '{name}': {e}")
