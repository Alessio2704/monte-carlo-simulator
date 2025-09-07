import os
from .exceptions import ValuaScriptError, ErrorCode
from .parser import parse_valuascript
from .validator import validate_semantics
from .optimizer import optimize_steps
from .linker import link_and_generate_bytecode


def _load_and_validate_module(module_path: str, processed_files: set, import_line: int):
    """
    Reads, parses, and validates a file to ensure it's a valid module.
    Returns the functions defined within it.
    """
    if module_path in processed_files:
        raise ValuaScriptError(ErrorCode.CIRCULAR_IMPORT, line=import_line, path=module_path)
    processed_files.add(module_path)

    try:
        with open(module_path, "r") as f:
            module_content = f.read()
    except FileNotFoundError:
        raise ValuaScriptError(ErrorCode.IMPORT_FILE_NOT_FOUND, line=import_line, path=module_path)

    module_ast = parse_valuascript(module_content)

    # Explicitly check that the imported file is declared as a module.
    if not any(d["name"] == "module" for d in module_ast.get("directives", [])):
        raise ValuaScriptError(ErrorCode.IMPORT_NOT_A_MODULE, line=import_line, path=module_path)

    # A module is validated by calling the main validator, which will enforce module-specific rules.
    # We pass an empty function map because modules cannot import other modules.
    validate_semantics(module_ast, {}, is_preview_mode=True)

    # Extract functions after successful validation
    user_functions = {}
    for func_def in module_ast.get("function_definitions", []):
        if func_def["name"] in user_functions:  # This check is now correctly inside the loader
            raise ValuaScriptError(ErrorCode.DUPLICATE_FUNCTION, line=func_def["line"], name=func_def["name"])
        user_functions[func_def["name"]] = func_def

    return user_functions


def compile_valuascript(script_content: str, optimize=False, verbose=False, preview_variable=None, context="cli", file_path=None):
    """
    Orchestrates the full compilation pipeline from a script string to a JSON bytecode recipe.
    """
    is_preview_mode = preview_variable is not None

    if is_preview_mode:
        optimize = True  # Always optimize for preview to remove irrelevant code

    if context == "lsp" and not script_content.strip():
        return None  # In LSP context, an empty file is not an error

    # 1. PARSING: Convert the main script to a high-level AST
    main_ast = parse_valuascript(script_content)

    # 2. Check if the main file itself is a module and handle it as a special case
    if any(d["name"] == "module" for d in main_ast.get("directives", [])):
        # If the main file is a module, it must be validated as one.
        validate_semantics(main_ast, {}, is_preview_mode=True)
        return {"simulation_config": {}, "variable_registry": [], "output_variable_index": None, "pre_trial_steps": [], "per_trial_steps": []}

    # 3. MODULE RESOLUTION (for runnable scripts)
    all_user_functions = {}
    base_dir = os.path.dirname(file_path) if file_path else ""
    processed_files = {os.path.abspath(file_path)} if file_path else set()

    for imp in main_ast.get("imports", []):
        if not file_path:
            raise ValuaScriptError(ErrorCode.CANNOT_IMPORT_FROM_STDIN, line=imp.get("line", 1))

        module_path = os.path.abspath(os.path.join(base_dir, imp["path"]))
        module_functions = _load_and_validate_module(module_path, processed_files, imp.get("line", 1))

        for name, func_def in module_functions.items():
            if name in all_user_functions:
                raise ValuaScriptError(ErrorCode.FUNCTION_NAME_COLLISION, line=imp.get("line", 1), name=name, path=module_path)
            all_user_functions[name] = func_def

    main_file_path_for_error = file_path or "<stdin>"
    for func_def in main_ast.get("function_definitions", []):
        if func_def["name"] in all_user_functions:
            raise ValuaScriptError(ErrorCode.FUNCTION_NAME_COLLISION, line=func_def["line"], name=func_def["name"], path=main_file_path_for_error)
        all_user_functions[func_def["name"]] = func_def

    # 4. SEMANTIC VALIDATION & INLINING
    inlined_steps, defined_vars, sim_config, output_var = validate_semantics(main_ast, all_user_functions, is_preview_mode)

    if is_preview_mode:
        output_var = preview_variable
        if output_var not in defined_vars:
            raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, name=output_var)

    # 5. OPTIMIZATION
    pre_trial_steps, per_trial_steps, stochastic_vars, final_defined_vars = optimize_steps(
        execution_steps=inlined_steps, output_var=output_var, defined_vars=defined_vars, do_dce=optimize, verbose=verbose
    )

    if is_preview_mode:
        is_stochastic = preview_variable in stochastic_vars
        sim_config["num_trials"] = 100 if is_stochastic else 1
        if preview_variable not in final_defined_vars:
            raise ValuaScriptError(ErrorCode.UNDEFINED_VARIABLE, name=preview_variable)

    # 6. LINKING & CODE GENERATION
    return link_and_generate_bytecode(pre_trial_steps, per_trial_steps, sim_config, output_var)