import pkgutil
import importlib

# The master dictionary that will hold all function signatures from all domains.
FUNCTION_SIGNATURES = {}

# Discover and import all modules in the current package (e.g., core.py, financial.py)
# This allows us to add new function domains just by adding a new file.
for _, name, _ in pkgutil.iter_modules(__path__):
    try:
        module = importlib.import_module(f".{name}", __name__)
        if hasattr(module, "SIGNATURES"):
            # Check for duplicate function names before merging
            for key in module.SIGNATURES:
                if key in FUNCTION_SIGNATURES:
                    # This is a developer error, not a user error.
                    raise NameError(f"Duplicate function signature '{key}' defined in 'vsc/functions/{name}.py'.")

            # Merge the signatures from the module into the master dictionary
            FUNCTION_SIGNATURES.update(module.SIGNATURES)
    except ImportError as e:
        # Handle potential import errors gracefully
        print(f"Warning: Could not import function signatures from '{name}': {e}")
