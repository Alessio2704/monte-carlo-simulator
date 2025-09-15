from lark import Token
from collections import deque
from .functions import FUNCTION_SIGNATURES
from .exceptions import ValuaScriptError


def _get_dependencies_from_arg(arg):
    """Recursively extracts variable dependencies from an argument or expression dict."""
    deps = set()
    if isinstance(arg, Token):
        deps.add(str(arg))
    elif isinstance(arg, dict):
        # Recurse into function arguments
        for sub_arg in arg.get("args", []):
            deps.update(_get_dependencies_from_arg(sub_arg))
        # Recurse into conditional expression branches
        if "condition" in arg:
            deps.update(_get_dependencies_from_arg(arg.get("condition")))
            deps.update(_get_dependencies_from_arg(arg.get("then_expr")))
            deps.update(_get_dependencies_from_arg(arg.get("else_expr")))
    return deps


def _get_step_results(step):
    """Helper to get a list of result variables from any step type."""
    return step.get("results") or [step.get("result")]


def _build_dependency_graph(execution_steps):
    """Builds forward (dependencies) and reverse (dependents) dependency graphs."""
    dependencies = {}

    # Initialize dependents for all variables that will be created
    dependents = {}
    for step in execution_steps:
        for res_var in _get_step_results(step):
            dependents[res_var] = set()

    for step in execution_steps:
        # The robust helper function can now parse the entire step dictionary
        step_deps = _get_dependencies_from_arg(step)
        for res_var in _get_step_results(step):
            dependencies[res_var] = step_deps

    for var, deps in dependencies.items():
        for dep in deps:
            if dep in dependents:
                dependents[dep].add(var)

    return dependencies, dependents


def _find_stochastic_variables(execution_steps, dependents):
    """Identifies all variables that are stochastic or depend on a stochastic variable."""
    stochastic_vars = set()
    queue = deque()

    def _expression_is_stochastic(expression_dict):
        """Recursively checks if any part of an expression is stochastic."""
        if not isinstance(expression_dict, dict):
            return False

        # Check for a direct stochastic function call
        func_name = expression_dict.get("function")
        if func_name and FUNCTION_SIGNATURES.get(func_name, {}).get("is_stochastic", False):
            return True

        # Recurse into function arguments
        for arg in expression_dict.get("args", []):
            if _expression_is_stochastic(arg):
                return True

        # Recurse into conditional expression branches
        if "condition" in expression_dict:
            # The condition itself cannot be stochastic, but the branches can be.
            if _expression_is_stochastic(expression_dict.get("then_expr")):
                return True
            if _expression_is_stochastic(expression_dict.get("else_expr")):
                return True

        return False

    for step in execution_steps:
        # Check the entire step for any stochastic sources
        if _expression_is_stochastic(step):
            for var_name in _get_step_results(step):
                if var_name not in stochastic_vars:
                    stochastic_vars.add(var_name)
                    queue.append(var_name)

    # Propagate stochasticity to all dependent variables
    while queue:
        current_var = queue.popleft()
        for dependent_var in dependents.get(current_var, []):
            if dependent_var not in stochastic_vars:
                stochastic_vars.add(dependent_var)
                queue.append(dependent_var)

    return stochastic_vars


def _find_live_variables(output_var, dependencies):
    """Finds all variables that the final output variable depends on."""
    live_vars = set()
    queue = deque([output_var])
    while queue:
        current_var = queue.popleft()
        if current_var not in live_vars:
            live_vars.add(current_var)
            for dep in dependencies.get(current_var, []):
                queue.append(dep)
    return live_vars


def _topological_sort_steps(steps, dependencies):
    """Sorts execution steps to ensure dependencies are calculated before they are used."""
    step_map = {}
    for step in steps:
        for res in _get_step_results(step):
            # Map each result var to its step. For multi-assign, they share a step.
            step_map[res] = step

    sorted_vars = []
    visited = set()
    recursion_stack = set()

    def visit(var):
        visited.add(var)
        recursion_stack.add(var)
        for dep in dependencies.get(var, []):
            if dep in recursion_stack:
                raise ValuaScriptError(f"Circular dependency detected involving variable '{var}'.")
            if dep not in visited and dep in step_map:
                visit(dep)
        recursion_stack.remove(var)
        sorted_vars.append(var)

    # Iterate through all variables defined in the steps to ensure all are visited
    all_step_vars = sorted(list(step_map.keys()))
    for var_name in all_step_vars:
        if var_name not in visited:
            visit(var_name)

    # Reconstruct the sorted list of steps, ensuring no duplicates for multi-assignments
    sorted_steps = []
    seen_steps = set()
    for var in sorted_vars:
        step = step_map[var]
        step_id = id(step)  # Use object ID to uniquely identify steps
        if step_id not in seen_steps:
            sorted_steps.append(step)
            seen_steps.add(step_id)

    return sorted_steps


def optimize_steps(execution_steps, output_var, defined_vars, do_dce, verbose):
    """Applies optimizations and partitions steps into pre-trial and per-trial phases."""
    dependencies, dependents = _build_dependency_graph(execution_steps)

    all_original_vars = set(dependents.keys())

    if do_dce:
        live_variables = _find_live_variables(output_var, dependencies)
        if verbose:
            print("\n--- Running Dead Code Elimination ---")

        # Filter steps based on whether ANY of their results are live
        original_step_count = len(execution_steps)
        execution_steps = [step for step in execution_steps if any(res in live_variables for res in _get_step_results(step))]

        removed_count = original_step_count - len(execution_steps)
        if removed_count > 0 and verbose:
            final_vars = set()
            for step in execution_steps:
                final_vars.update(_get_step_results(step))
            removed_vars = sorted(list(all_original_vars - final_vars))
            print(f"Optimization complete: Removed {len(removed_vars)} unused variable(s): {', '.join(removed_vars)}")
        elif verbose:
            print("Optimization complete: No unused variables found to remove.")
        # Rebuild dependency graph after DCE
        dependencies, dependents = _build_dependency_graph(execution_steps)

    if verbose:
        print(f"\n--- Running Loop-Invariant Code Motion ---")

    stochastic_vars = _find_stochastic_variables(execution_steps, dependents)

    pre_trial_steps_raw, per_trial_steps_raw = [], []
    for step in execution_steps:
        # A step is per-trial if ANY of its results are stochastic
        if any(res in stochastic_vars for res in _get_step_results(step)):
            per_trial_steps_raw.append(step)
        else:
            pre_trial_steps_raw.append(step)

    # Topologically sort the pre-trial (deterministic) steps
    pre_trial_vars = set()
    for step in pre_trial_steps_raw:
        pre_trial_vars.update(_get_step_results(step))
    pre_trial_dependencies = {k: v for k, v in dependencies.items() if k in pre_trial_vars}
    pre_trial_steps_sorted = _topological_sort_steps(pre_trial_steps_raw, pre_trial_dependencies)

    if verbose and pre_trial_steps_sorted:
        moved_vars = []
        for step in pre_trial_steps_sorted:
            moved_vars.extend(_get_step_results(step))
        print(f"Optimization complete: Moved {len(pre_trial_steps_sorted)} deterministic step(s) to the pre-trial phase, defining: {', '.join(sorted(moved_vars))}")

    # Update defined_vars to reflect any removed variables from DCE
    final_vars_set = set()
    for step in pre_trial_steps_sorted + per_trial_steps_raw:
        final_vars_set.update(_get_step_results(step))
    final_defined_vars = {k: v for k, v in defined_vars.items() if k in final_vars_set}

    return pre_trial_steps_sorted, per_trial_steps_raw, stochastic_vars, final_defined_vars
