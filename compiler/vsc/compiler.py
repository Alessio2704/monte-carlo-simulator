import os
from .exceptions import ValuaScriptError, ErrorCode
from .parser import parse_valuascript
from .validator import validate_semantics
from .optimizer import optimize_steps
from .linker import link_and_generate_bytecode


def _load_and_validate_module(module_path: str, base_dir: str, all_user_functions: dict, processed_files: set, import_line: int):
    """
    Recursively reads, parses, and validates a module and all of its dependencies.
    """
    abs_module_path = os.path.abspath(os.path.join(base_dir, module_path))
    if abs_module_path in processed_files:
        raise ValuaScriptError(ErrorCode.CIRCULAR_IMPORT, line=import_line, path=module_path)
    processed_files.add(abs_module_path)

    try:
        with open(abs_module_path, "r") as f:
            module_content = f.read()
    except FileNotFoundError:
        raise ValuaScriptError(ErrorCode.IMPORT_FILE_NOT_FOUND, line=import_line, path=module_path)

    module_ast = parse_valuascript(module_content)
    module_base_dir = os.path.dirname(abs_module_path)

    if not any(d["name"] == "module" for d in module_ast.get("directives", [])):
        raise ValuaScriptError(ErrorCode.IMPORT_NOT_A_MODULE, line=import_line, path=module_path)

    # First, handle nested imports.
    for imp in module_ast.get("imports", []):
        _load_and_validate_module(imp["path"], module_base_dir, all_user_functions, processed_files, imp.get("line", 1))

    # Second, check for internal duplicates within this module.
    module_internal_functions = {}
    for func_def in module_ast.get("function_definitions", []):
        name = func_def["name"]
        if name in module_internal_functions:
            raise ValuaScriptError(ErrorCode.DUPLICATE_FUNCTION, line=func_def["line"], name=name)
        module_internal_functions[name] = func_def

    # Third, check for collisions against already loaded functions and add them to the global map.
    for name, func_def in module_internal_functions.items():
        if name in all_user_functions:
            raise ValuaScriptError(ErrorCode.FUNCTION_NAME_COLLISION, line=func_def["line"], name=name, path=module_path)
        all_user_functions[name] = func_def

    # Finally, validate this module's internal semantics.
    validate_semantics(module_ast, all_user_functions, is_preview_mode=True)


def resolve_imports_and_functions(main_ast, file_path):
    """
    Parses the import graph and gathers all user-defined functions from the
    main file and all imported modules, checking for duplicates and collisions.
    Returns a dictionary of all user-defined functions.
    """
    all_user_functions = {}
    processed_files = {os.path.abspath(file_path)} if file_path else set()
    base_dir = os.path.dirname(file_path) if file_path else ""
    main_file_path_for_error = file_path or "<stdin>"

    # 1. Process imports first.
    for imp in main_ast.get("imports", []):
        if not file_path:
            raise ValuaScriptError(ErrorCode.CANNOT_IMPORT_FROM_STDIN, line=imp.get("line", 1))
        _load_and_validate_module(imp["path"], base_dir, all_user_functions, processed_files, imp.get("line", 1))

    # 2. Check for internal duplicates in the main file.
    main_file_functions = {}
    for func_def in main_ast.get("function_definitions", []):
        name = func_def["name"]
        if name in main_file_functions:
            raise ValuaScriptError(ErrorCode.DUPLICATE_FUNCTION, line=func_def["line"], name=name)
        main_file_functions[name] = func_def

    # 3. Check for collisions between main file functions and imported functions.
    for name, func_def in main_file_functions.items():
        if name in all_user_functions:
            raise ValuaScriptError(ErrorCode.FUNCTION_NAME_COLLISION, line=func_def["line"], name=name, path=main_file_path_for_error)
        all_user_functions[name] = func_def

    return all_user_functions


def compile_valuascript(script_content: str, optimize=False, verbose=False, preview_variable=None, context="cli", file_path=None):
    """
    Orchestrates the full compilation pipeline from a script string to a JSON bytecode recipe.
    """
    is_preview_mode = preview_variable is not None
    if is_preview_mode:
        optimize = True

    if context == "lsp" and not script_content.strip():
        return None

    main_ast = parse_valuascript(script_content)

    # Use the public helper to resolve all imports and functions.
    all_user_functions = resolve_imports_and_functions(main_ast, file_path)

    # If the entry point is a module, validate it and we're done.
    if any(d["name"] == "module" for d in main_ast.get("directives", [])):
        validate_semantics(main_ast, all_user_functions, is_preview_mode=True)
        return {"simulation_config": {}, "variable_registry": [], "output_variable_index": None, "pre_trial_steps": [], "per_trial_steps": []}

    # Otherwise, continue the full compilation pipeline for a runnable script.
    inlined_steps, defined_vars, sim_config, output_var = validate_semantics(main_ast, all_user_functions, is_preview_mode)

    if is_preview_mode:
        output_var = preview_variable
        if output_var not in defined_vars:
            raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, name=output_var)

    pre_trial_steps, per_trial_steps, stochastic_vars, final_defined_vars = optimize_steps(
        execution_steps=inlined_steps, output_var=output_var, defined_vars=defined_vars, do_dce=optimize, verbose=verbose
    )

    if is_preview_mode:
        is_stochastic = preview_variable in stochastic_vars
        sim_config["num_trials"] = 100 if is_stochastic else 1
        if preview_variable not in final_defined_vars:
            raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, name=preview_variable)

    return link_and_generate_bytecode(pre_trial_steps, per_trial_steps, sim_config, output_var)