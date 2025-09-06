from .exceptions import ValuaScriptError
from .parser import parse_valuascript
from .validator import validate_semantics
from .optimizer import optimize_steps
from .linker import link_and_generate_bytecode


def compile_valuascript(script_content: str, optimize=False, verbose=False, preview_variable=None, context="cli"):
    """
    Orchestrates the full compilation pipeline from a script string to a JSON bytecode recipe.
    """
    is_preview_mode = preview_variable is not None

    if is_preview_mode:
        optimize = True  # Always optimize for preview to remove irrelevant code

    if context == "lsp" and not script_content.strip():
        return None  # In LSP context, an empty file is not an error

    # 1. PARSING: Convert raw text to a high-level AST
    high_level_ast = parse_valuascript(script_content)

    # 2. SEMANTIC VALIDATION & INLINING: Check for errors and flatten UDFs
    # This also validates and extracts directives.
    inlined_steps, defined_vars, sim_config, output_var = validate_semantics(high_level_ast, is_preview_mode)

    # Handle preview mode logic, which overrides directives
    if is_preview_mode:
        output_var = preview_variable
        if output_var not in defined_vars:
            raise ValuaScriptError(f"The final @output variable '{output_var}' is not defined.")

    # 3. OPTIMIZATION: Perform DCE and partition into pre/per-trial steps
    pre_trial_steps, per_trial_steps, stochastic_vars, final_defined_vars = optimize_steps(
        execution_steps=inlined_steps,
        output_var=output_var,
        defined_vars=defined_vars,
        do_dce=optimize,
        verbose=verbose,
    )

    # Re-evaluate number of trials for preview mode after optimizations
    if is_preview_mode:
        is_stochastic = preview_variable in stochastic_vars
        sim_config["num_trials"] = 100 if is_stochastic else 1
        # Also need to re-check if the preview var was eliminated
        if preview_variable not in final_defined_vars:
            raise ValuaScriptError(f"The preview variable '{preview_variable}' is not defined or was eliminated as unused code.")

    # 4. LINKING & CODE GENERATION: Build registry and create low-level bytecode
    final_recipe = link_and_generate_bytecode(
        pre_trial_steps=pre_trial_steps,
        per_trial_steps=per_trial_steps,
        sim_config=sim_config,
        output_var=output_var,
    )

    return final_recipe 