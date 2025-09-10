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


def _build_dependency_graph(execution_steps):
    """Builds forward (dependencies) and reverse (dependents) dependency graphs."""
    dependencies = {}
    dependents = {step["result"]: set() for step in execution_steps}

    for step in execution_steps:
        var_name = step["result"]
        # The robust helper function can now parse the entire step dictionary,
        # regardless of whether it's an execution_assignment or conditional_expression.
        dependencies[var_name] = _get_dependencies_from_arg(step)

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
            var_name = step["result"]
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
    step_map = {step["result"]: step for step in steps}
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

    for step in steps:
        var_name = step["result"]
        if var_name not in visited:
            visit(var_name)

    return [step_map[var] for var in sorted_vars]


def optimize_steps(execution_steps, output_var, defined_vars, do_dce, verbose):
    """Applies optimizations and partitions steps into pre-trial and per-trial phases."""
    dependencies, dependents = _build_dependency_graph(execution_steps)

    if do_dce:
        live_variables = _find_live_variables(output_var, dependencies)
        if verbose:
            print("\n--- Running Dead Code Elimination ---")
        original_step_count = len(execution_steps)
        all_original_vars = {step["result"] for step in execution_steps}
        execution_steps = [step for step in execution_steps if step["result"] in live_variables]
        removed_count = original_step_count - len(execution_steps)
        if removed_count > 0 and verbose:
            removed_vars = sorted(list(all_original_vars - live_variables))
            print(f"Optimization complete: Removed {removed_count} unused variable(s): {', '.join(removed_vars)}")
        elif verbose:
            print("Optimization complete: No unused variables found to remove.")
        # Rebuild dependency graph after DCE
        dependencies, dependents = _build_dependency_graph(execution_steps)

    if verbose:
        print(f"\n--- Running Loop-Invariant Code Motion ---")

    stochastic_vars = _find_stochastic_variables(execution_steps, dependents)

    pre_trial_steps_raw, per_trial_steps_raw = [], []
    for step in execution_steps:
        if step["result"] in stochastic_vars:
            per_trial_steps_raw.append(step)
        else:
            pre_trial_steps_raw.append(step)

    # Topologically sort the pre-trial (deterministic) steps
    pre_trial_dependencies = {k: v for k, v in dependencies.items() if k in {s["result"] for s in pre_trial_steps_raw}}
    pre_trial_steps_sorted = _topological_sort_steps(pre_trial_steps_raw, pre_trial_dependencies)

    if verbose and pre_trial_steps_sorted:
        moved_vars = sorted([step["result"] for step in pre_trial_steps_sorted])
        print(f"Optimization complete: Moved {len(pre_trial_steps_sorted)} deterministic step(s) to the pre-trial phase: {', '.join(moved_vars)}")

    # Update defined_vars to reflect any removed variables from DCE
    final_vars = {step["result"] for step in pre_trial_steps_sorted + per_trial_steps_raw}
    final_defined_vars = {k: v for k, v in defined_vars.items() if k in final_vars}

    return pre_trial_steps_sorted, per_trial_steps_raw, stochastic_vars, final_defined_vars
