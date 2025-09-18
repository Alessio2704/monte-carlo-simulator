from typing import List, Dict, Any, Optional
from lark import Token

# from .data_structures import FileSemanticModel # The model is treated as a dict
from .parser import _StringLiteral


class IRGenerator:
    """
    Generates a linear Intermediate Representation (IR) from the validated
    semantic model. It flattens the execution flow by inlining all
    user-defined functions (UDFs) and transforming the AST into a simple
    list of assignment instructions.
    """

    def __init__(self, model: Dict[str, Any]):
        self.model = model
        self.ir: List[Dict[str, Any]] = []
        self.udf_call_counters: Dict[str, int] = {}
        self.temp_var_count = 0

    def generate(self) -> List[Dict[str, Any]]:
        """Main entry point to generate the IR for the entire script."""
        main_ast = self.model["processed_asts"][self.model["main_file_path"]]
        execution_steps = main_ast.get("execution_steps", [])

        for step in execution_steps:
            self._process_step(step)

        return self.ir

    def _process_step(self, step: Dict[str, Any], context: Optional[Dict[str, str]] = None):
        """
        Processes a single AST step and appends the corresponding
        instruction(s) to the IR.
        """
        step_type = step.get("type")

        if step_type == "literal_assignment":
            self._add_literal_assignment(step, context)
        elif step_type == "conditional_expression":
            self._add_conditional_assignment(step, context)
        elif step_type in ("execution_assignment", "multi_assignment"):
            self._process_execution_assignment(step, context)

    def _add_literal_assignment(self, step: Dict[str, Any], context: Optional[Dict[str, str]]):
        """Handles `let x = 1`, `let y = [1,2,3]`, etc."""
        result_vars = [step["result"]]
        value = self._transform_expression(step["value"], context)

        self.ir.append({"type": "literal_assignment", "result": self._mangle_vars(result_vars, context), "value": value, "line": step["line"]})

    def _add_conditional_assignment(self, step: Dict[str, Any], context: Optional[Dict[str, str]]):
        """Handles `let x = if cond then 1 else 0`."""
        result_vars = [step["result"]]
        self.ir.append(
            {
                "type": "conditional_assignment",
                "result": self._mangle_vars(result_vars, context),
                "condition": self._transform_expression(step["condition"], context),
                "then_expr": self._transform_expression(step["then_expr"], context),
                "else_expr": self._transform_expression(step["else_expr"], context),
                "line": step["line"],
            }
        )

    def _process_execution_assignment(self, step: Dict[str, Any], context: Optional[Dict[str, str]]):
        """Handles function calls, dispatching to UDF inlining if necessary."""
        func_name = step.get("function")

        if func_name in self.model["user_defined_functions"]:
            self._inline_udf_call(step, context)
        else:
            # This is a built-in function call
            result_vars = step.get("results") or [step.get("result")]
            self.ir.append(
                {
                    "type": "execution_assignment",
                    "result": self._mangle_vars(result_vars, context),
                    "function": func_name,
                    "args": [self._transform_expression(arg, context) for arg in step.get("args", [])],
                    "line": step["line"],
                }
            )

    def _inline_udf_call(self, call_step: Dict[str, Any], context: Optional[Dict[str, str]]):
        """
        The core of the IR generator. Replaces a UDF call with its body,
        mangling all local variables and parameters to prevent name collisions.
        """
        func_name = call_step["function"]
        func_def = self.model["user_defined_functions"][func_name]

        call_id = self.udf_call_counters.get(func_name, 0) + 1
        self.udf_call_counters[func_name] = call_id

        def mangle(name: str) -> str:
            return f"__{func_name}_{call_id}__{name}"

        mangled_context = {p["name"]: mangle(p["name"]) for p in func_def["params"]}
        mangled_context.update({name: mangle(name) for name in func_def["discovered_body"]})

        for i, param in enumerate(func_def["params"]):
            self.ir.append(
                {
                    "type": "execution_assignment",
                    "result": [mangle(param["name"])],
                    "function": "identity",
                    "args": [self._transform_expression(call_step["args"][i], context)],
                    "line": call_step["line"],
                }
            )

        for body_step in func_def["ast_body"]:
            if body_step["type"] == "return_statement":
                original_results = call_step.get("results") or [call_step.get("result")]
                return_node = body_step.get("value") or body_step.get("values")
                line = call_step["line"]

                transformed_return_expr = self._transform_expression(return_node, mangled_context)

                if isinstance(transformed_return_expr, dict) and "function" in transformed_return_expr:
                    self.ir.append(
                        {
                            "type": "execution_assignment",
                            "result": self._mangle_vars(original_results, context),
                            "function": transformed_return_expr["function"],
                            "args": transformed_return_expr["args"],
                            "line": line,
                        }
                    )
                elif isinstance(transformed_return_expr, Token):
                    self.ir.append(
                        {
                            "type": "execution_assignment",
                            "result": self._mangle_vars(original_results, context),
                            "function": "identity",
                            "args": [transformed_return_expr],
                            "line": line,
                        }
                    )
                else:
                    if body_step.get("values"):
                        self.ir.append(
                            {
                                "type": "execution_assignment",
                                "result": self._mangle_vars(original_results, context),
                                "function": "identity",
                                "args": [transformed_return_expr],
                                "line": line,
                            }
                        )
                    else:
                        self.ir.append(
                            {
                                "type": "literal_assignment",
                                "result": self._mangle_vars(original_results, context),
                                "value": transformed_return_expr,
                                "line": line,
                            }
                        )
            else:
                self._process_step(body_step, mangled_context)

    def _transform_expression(self, expr: Any, context: Optional[Dict[str, str]]) -> Any:
        """
        Recursively transforms an AST expression into an IR-compatible format.
        It resolves variable names within a given context (mangled or global)
        and preserves nested function calls as JSON objects.
        """
        if isinstance(expr, (int, float, bool)):
            return expr
        if isinstance(expr, _StringLiteral):
            return expr.value
        if isinstance(expr, Token):
            return Token("CNAME", self._mangle_vars([expr.value], context)[0])
        if isinstance(expr, list):
            return [self._transform_expression(item, context) for item in expr]

        if isinstance(expr, dict):
            if expr.get("_is_vector_literal"):
                return [self._transform_expression(item, context) for item in expr["items"]]
            if expr.get("type") == "conditional_expression":
                return {
                    "type": "conditional_expression",
                    "condition": self._transform_expression(expr["condition"], context),
                    "then_expr": self._transform_expression(expr["then_expr"], context),
                    "else_expr": self._transform_expression(expr["else_expr"], context),
                }
            if "function" in expr:
                func_name = expr["function"]
                if func_name in self.model["user_defined_functions"]:
                    self.temp_var_count += 1
                    temp_var_name = f"__temp_{self.temp_var_count}"

                    # FIX: Create a standard single-assignment step with a 'result' (string) key.
                    nested_call_step = {"type": "execution_assignment", "result": temp_var_name, "function": func_name, "args": expr["args"], "line": expr.get("line", -1)}
                    self._inline_udf_call(nested_call_step, context)
                    return Token("CNAME", temp_var_name)
                else:
                    return {
                        "function": func_name,
                        "args": [self._transform_expression(arg, context) for arg in expr.get("args", [])],
                    }
        raise TypeError(f"Internal Error: Unhandled type '{type(expr).__name__}' during IR generation.")

    def _mangle_vars(self, var_names: List[str], context: Optional[Dict[str, str]]) -> List[str]:
        """Applies a name mangling context to a list of variable names."""
        if not context:
            return var_names
        return [context.get(name, name) for name in var_names]


def generate_ir(model: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    High-level entry point for the IR generation stage.
    """
    generator = IRGenerator(model)
    return generator.generate()
