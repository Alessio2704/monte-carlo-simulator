from typing import List, Dict, Any, Set


class IRValidationError(Exception):
    """Custom exception for IR integrity failures."""

    def __init__(self, message, step_index, step, undefined_variable):
        full_message = f"IR Validation Failed at step {step_index}:\n" f"--> Undefined variable '{undefined_variable}' used.\n" f"--> Offending Step: {step}\n"
        super().__init__(full_message)
        self.step_index = step_index
        self.step = step
        self.undefined_variable = undefined_variable


class IRValidator:
    """
    Verifies the data-flow integrity of a linear IR.
    It ensures that every variable used in an instruction has been defined
    in a preceding instruction.
    """

    def __init__(self, ir: List[Dict[str, Any]]):
        self.ir = ir
        self.defined_vars: Set[str] = set()
        self.current_step_index = -1

    def validate(self):
        """
        Runs the validation process.
        Raises IRValidationError if an inconsistency is found.
        """
        for i, step in enumerate(self.ir):
            self.current_step_index = i

            # 1. Find and validate all input variables for the current step.
            used_vars = self._find_used_variables(step)
            for var in used_vars:
                if var not in self.defined_vars:
                    raise IRValidationError("Undefined variable usage.", step_index=i, step=step, undefined_variable=var)

            # 2. Add the output variables of this step to the defined set.
            result_vars = step.get("result") or step.get("results", [])
            for var in result_vars:
                self.defined_vars.add(var)

    def _find_used_variables(self, node: Any) -> Set[str]:
        """
        Recursively traverses an expression node to find all variable names used.
        """
        used = set()
        if isinstance(node, str):
            # In our IR, any string that is not a function name is a variable.
            # We assume the structure is valid enough for this check.
            # This check is simplistic; a more robust one might ignore dict keys.
            used.add(node)
            return used

        if isinstance(node, list):
            for item in node:
                used.update(self._find_used_variables(item))
            return used

        if isinstance(node, dict):
            # We are interested in the values that represent variables or sub-expressions.
            # We deliberately skip keys like "type", "function", "result" etc.
            keys_to_scan = ["args", "condition", "then_expr", "else_expr"]
            for key in keys_to_scan:
                if key in node:
                    used.update(self._find_used_variables(node[key]))
            return used

        # It's a literal (int, bool, float), so we ignore it.
        return used
