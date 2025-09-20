from typing import List, Dict, Any


class TupleForwarder:
    """
    Performs the Tuple Forwarding optimization phase.

    This pass finds multi-assignments from redundant 'identity' calls and
    forwards the results from the source instruction directly, eliminating
    the intermediate temporary variables and the identity call.
    """

    def optimize(self, ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        This optimization is performed in a loop to handle cases where one
        forwarding operation might enable another in a subsequent pass.
        """
        # We create a new copy to modify while iterating
        optimized_ir = ir[:]

        while True:
            made_change = False
            identity_index_to_remove = -1

            # Find the first forwarding opportunity in the current IR
            for i, step in enumerate(optimized_ir):
                is_identity = step.get("function") == "identity"
                # This pattern is specifically for multi-assignments
                is_multi_assign = len(step.get("result", [])) > 1

                if is_identity and is_multi_assign:
                    args = step.get("args", [])
                    # The specific pattern from the IR generator is args:[[vars...]]
                    if len(args) == 1 and isinstance(args[0], list) and all(isinstance(v, str) for v in args[0]):
                        source_vars = args[0]
                        target_vars = step["result"]

                        if len(source_vars) == len(target_vars):
                            # We found an opportunity. Now find the instruction that defines the source_vars.
                            source_def_index = -1
                            for j in range(i - 1, -1, -1):
                                if optimized_ir[j].get("result") == source_vars:
                                    source_def_index = j
                                    break

                            if source_def_index != -1:
                                # We found both parts. Perform the transformation.
                                # 1. The source instruction now produces the final target variables.
                                optimized_ir[source_def_index]["result"] = target_vars

                                # 2. Mark the identity instruction for removal.
                                identity_index_to_remove = i
                                made_change = True
                                break  # Exit the inner loop to restart the process

            if made_change:
                # Rebuild the IR without the removed identity instruction
                optimized_ir = [step for i, step in enumerate(optimized_ir) if i != identity_index_to_remove]
                # Loop again to find other opportunities in the now-modified IR
                continue
            else:
                # If we went through a full pass with no changes, we are done.
                break

        return optimized_ir


def run_tuple_forwarding(ir: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-level entry point for the tuple forwarding optimization phase."""
    optimizer = TupleForwarder()
    return optimizer.optimize(ir)
