from typing import List, Dict, Any, Set


class IRValidationError(Exception):
    """Custom exception for IR integrity failures."""

    def __init__(self, message, step_index, step, undefined_variables: List[str]):
        vars_str = ", ".join([f"'{v}'" for v in undefined_variables])
        full_message = f"\n\nIR VALIDATION FAILED at step {step_index}:\n" f"--> The following variable(s) were used before being defined: {vars_str}.\n" f"--> Offending Step: {step}\n"
        super().__init__(full_message)
        self.step_index = step_index
        self.step = step
        self.undefined_variables = undefined_variables


class IRValidator:
    """
    Verifies the data-flow integrity of a linear IR.
    It ensures that every variable used in an instruction has been defined
    in a preceding instruction.
    """

    def __init__(self, ir: List[Dict[str, Any]]):
        self.ir = ir
        self.defined_vars: Set[str] = set()

    def validate(self):
        """
        Runs the validation process. Finds all undefined variables per step
        and raises a single, comprehensive error if any are found.
        """
        for i, step in enumerate(self.ir):
            # 1. Find all variables used as INPUTS in the current step.
            # This is now done by the much more precise _find_used_variables method.
            used_vars_candidates = self._find_used_variables(step)

            # 2. Filter this list to find which ones are actually undefined.
            undefined_vars = [var for var in used_vars_candidates if var not in self.defined_vars]

            # 3. If any are found, raise a single, comprehensive error.
            if undefined_vars:
                raise IRValidationError("Undefined variable usage.", step_index=i, step=step, undefined_variables=sorted(list(set(undefined_vars))))

            # 4. If the step is valid, add its OUTPUT variables to the defined set.
            result_vars = step.get("result", [])
            for var in result_vars:
                self.defined_vars.add(var)

    def _find_used_variables(self, node: Any) -> Set[str]:
        """
        Recursively traverses an expression node to find all variable names
        used as inputs.
        """
        used = set()

        # Base case 1: If it's a string, it's a potential variable name.
        if isinstance(node, str):
            used.add(node)
            return used

        # Base case 2: If it's a number or boolean, it's a literal, not a variable.
        if not isinstance(node, (dict, list)):
            return used

        # Recursive case for lists (e.g., inside 'args')
        if isinstance(node, list):
            for item in node:
                used.update(self._find_used_variables(item))
            return used

        # Recursive and SPECIFIC case for dictionaries.
        # We no longer iterate over all values. We only look inside keys
        # that are known to hold input expressions.
        if isinstance(node, dict):
            # These are the only fields in our IR that can contain variable inputs.
            # We explicitly ignore "type", "result", "function", "line", etc.
            keys_with_inputs = ["args", "condition", "then_expr", "else_expr"]

            for key in keys_with_inputs:
                if key in node:
                    used.update(self._find_used_variables(node[key]))

            return used

        return used
