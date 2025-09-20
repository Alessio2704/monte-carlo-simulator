from typing import List, Dict, Any


class AliasResolver:
    """
    Performs the Alias Resolution optimization phase.

    This pass is a more powerful version of forwarding that specifically handles
    the aliasing created by UDF return statements (e.g., `let x = identity(__temp_x)`).
    It finds these simple identity assignments, rewrites the original instruction
    that produced the temporary variable to use the final variable name, and
    eliminates the identity instruction.

    This is crucial for restoring user-defined variable names in the final IR.
    """

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        optimized_ir = ir[:]

        while True:
            made_change = False
            identity_index_to_remove = -1

            # Find the first aliasing opportunity
            for i, step in enumerate(optimized_ir):
                is_identity = step.get("function") == "identity"
                # This pass is for single variables
                is_single_assign = len(step.get("result", [])) == 1

                if is_identity and is_single_assign:
                    args = step.get("args", [])
                    # The argument must be a single string (a variable name)
                    if len(args) == 1 and isinstance(args[0], str):
                        source_var = args[0]
                        target_var = step["result"][0]

                        # Find the instruction that defines the source variable
                        source_def_index = -1
                        for j in range(i - 1, -1, -1):
                            # The source must also be a single-result instruction
                            source_results = optimized_ir[j].get("result", [])
                            if len(source_results) == 1 and source_results[0] == source_var:
                                source_def_index = j
                                break

                        if source_def_index != -1:
                            # We found the whole pattern. Transform the IR.
                            # 1. The source instruction now produces the final target variable.
                            optimized_ir[source_def_index]["result"] = [target_var]

                            # 2. Mark the identity instruction for removal.
                            identity_index_to_remove = i
                            made_change = True
                            break  # Restart the scan on the modified IR

            if made_change:
                optimized_ir = [step for i, step in enumerate(optimized_ir) if i != identity_index_to_remove]
                continue
            else:
                break

        return optimized_ir


def run_alias_resolver(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the alias resolution optimization phase."""
    optimizer = AliasResolver()
    return optimizer.optimize(ir)
