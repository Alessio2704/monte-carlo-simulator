import pkgutil
import importlib


FUNCTION_SIGNATURES = {}


for _, name, _ in pkgutil.iter_modules(__path__):
    try:
        module = importlib.import_module(f".{name}", __name__)
        if hasattr(module, "SIGNATURES"):

            for key in module.SIGNATURES:
                if key in FUNCTION_SIGNATURES:

                    raise NameError(f"Duplicate function signature '{key}' defined in 'vsc/functions/{name}.py'.")

            FUNCTION_SIGNATURES.update(module.SIGNATURES)
    except ImportError as e:

        print(f"Warning: Could not import function signatures from '{name}': {e}")
