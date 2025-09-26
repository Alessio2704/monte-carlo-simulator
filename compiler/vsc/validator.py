from lark import Token
from collections import deque
import os

from .exceptions import ValuaScriptError, ErrorCode
from .parser.parser import _StringLiteral
from .config import DIRECTIVE_CONFIG
from .functions import FUNCTION_SIGNATURES


class SemanticAnalyzer:
    """
    Performs a deep, non-destructive analysis of a script and its imports.
    It builds a rich symbol table containing types, scopes, and locations
    for all variables and functions, which can be used by the LSP and compiler.
    """

    def __init__(self, main_ast, all_user_functions, file_path):
        self.main_ast = main_ast
        self.all_user_functions = all_user_functions
        self.file_path = file_path
        self.is_module = any(d["name"] == "module" for d in main_ast.get("directives", []))
        self.udf_signatures = {name: {"variadic": False, "arg_types": [p["type"] for p in fdef["params"]], "return_type": fdef["return_type"]} for name, fdef in self.all_user_functions.items()}
        self.all_signatures = {**FUNCTION_SIGNATURES, **self.udf_signatures}

        # This will store the final, rich analysis result.
        self.analysis = {"global_scope": {"variables": {}, "functions": {}}, "udf_scopes": {}}

    def analyze(self):
        """Main entry point for the analysis."""
        self._validate_directives()
        self._validate_function_definitions()
        self._analyze_scopes()
        return self.analysis

    def _validate_directives(self):
        directives = {}
        for d in self.main_ast.get("directives", []):
            name, line = d["name"], d["line"]
            if name not in DIRECTIVE_CONFIG:
                raise ValuaScriptError(ErrorCode.UNKNOWN_DIRECTIVE, line=line, name=name)
            if name in directives:
                raise ValuaScriptError(ErrorCode.DUPLICATE_DIRECTIVE, line=line, name=name)
            directives[name] = d

        if self.is_module:
            if self.main_ast.get("execution_steps"):
                raise ValuaScriptError(ErrorCode.GLOBAL_LET_IN_MODULE, line=self.main_ast["execution_steps"][0]["line"])
            for name, d in directives.items():
                if not DIRECTIVE_CONFIG[name]["allowed_in_module"]:
                    raise ValuaScriptError(ErrorCode.DIRECTIVE_NOT_ALLOWED_IN_MODULE, line=d["line"], name=name)
        else:
            for name, config in DIRECTIVE_CONFIG.items():
                if name in ["import", "module"]:
                    continue
                is_req = config["required"](directives) if callable(config["required"]) else config["required"]
                if is_req and name not in directives:
                    code = ErrorCode.MISSING_ITERATIONS_DIRECTIVE if name == "iterations" else ErrorCode.MISSING_OUTPUT_DIRECTIVE
                    raise ValuaScriptError(code)

    def _validate_function_definitions(self):
        RESERVED_NAMES = set(FUNCTION_SIGNATURES.keys())
        for name, func_def in self.all_user_functions.items():
            if name in RESERVED_NAMES:
                raise ValuaScriptError(ErrorCode.REDEFINE_BUILTIN_FUNCTION, line=func_def["line"], name=name)
        self._check_for_recursive_calls()

    def _analyze_scopes(self):
        # --- Analyze Global Scope ---
        global_vars = self.analysis["global_scope"]["variables"]
        for step in self.main_ast.get("execution_steps", []):
            self._analyze_assignment(step, global_vars, "global")

        # --- Analyze UDF Scopes ---
        for func_name, func_def in self.all_user_functions.items():
            if func_def.get("source_path") != self.file_path:
                continue  # Only analyze functions defined in the current file

            scope_name = func_name
            self.analysis["udf_scopes"][scope_name] = {
                "name": func_name,
                "line": func_def["line"],
                "params": func_def["params"],
                "return_type": func_def["return_type"],
                "docstring": func_def.get("docstring"),
                "variables": {},
            }
            local_vars = self.analysis["udf_scopes"][scope_name]["variables"]

            # Add parameters to the local scope
            for param in func_def.get("params", []):
                local_vars[param["name"]] = {
                    "name": param["name"],
                    "type": param["type"],
                    "is_stochastic": False,
                    "line": func_def["line"],
                }

            # Analyze the function body
            has_return = False
            for step in func_def.get("body", []):
                if step.get("type") == "return_statement":
                    has_return = True
                    self._validate_return_statement(step, local_vars, func_def)
                else:
                    self._analyze_assignment(step, local_vars, scope_name)

            if not has_return:
                raise ValuaScriptError(ErrorCode.MISSING_RETURN_STATEMENT, line=func_def["line"], name=func_name)

    def _analyze_assignment(self, step, scope_vars, scope_name):
        line = step["line"]
        is_multi = step["type"] == "multi_assignment"

        var_names = step["results"] if is_multi else [step["result"]]
        for var_name in var_names:
            if var_name in scope_vars:
                err_code = ErrorCode.DUPLICATE_VARIABLE_IN_FUNC if scope_name != "global" else ErrorCode.DUPLICATE_VARIABLE
                raise ValuaScriptError(err_code, line=line, name=var_name, func_name=scope_name)

        inferred_types = self._infer_expression_type(step["expression"], scope_vars, line, scope_name)

        if is_multi:
            if not isinstance(inferred_types, list) or len(inferred_types) != len(var_names):
                raise ValuaScriptError(
                    ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=f"assignment", expected=len(var_names), provided=len(inferred_types) if isinstance(inferred_types, list) else 1
                )
            for i, var_name in enumerate(var_names):
                scope_vars[var_name] = {"name": var_name, "type": inferred_types[i], "line": line, "is_stochastic": False}
        else:
            if isinstance(inferred_types, list):
                raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=f"assignment", expected=1, provided=len(inferred_types))
            scope_vars[var_names[0]] = {"name": var_names[0], "type": inferred_types, "line": line, "is_stochastic": False}

    def _validate_return_statement(self, step, local_vars, func_def):
        line, func_name = step["line"], func_def["name"]
        expected_type = func_def["return_type"]

        if "values" in step:  # Tuple return
            actual_types = [self._infer_expression_type(val, local_vars, line, func_name) for val in step["values"]]
            if not isinstance(expected_type, list) or len(expected_type) != len(actual_types):
                raise ValuaScriptError(ErrorCode.RETURN_TYPE_MISMATCH, line=line, name=func_name, expected=f"a tuple of {len(expected_type)} items", provided=f"a tuple of {len(actual_types)} items")
            for i, (exp, act) in enumerate(zip(expected_type, actual_types)):
                if exp != act:
                    raise ValuaScriptError(ErrorCode.RETURN_TYPE_MISMATCH, line=line, name=f"{func_name} (return item {i+1})", expected=exp, provided=act)
        else:  # Single return
            actual_type = self._infer_expression_type(step["value"], local_vars, line, func_name)
            if isinstance(expected_type, list) or actual_type != expected_type:
                raise ValuaScriptError(ErrorCode.RETURN_TYPE_MISMATCH, line=line, name=func_name, expected=str(expected_type), provided=str(actual_type))

    def _infer_expression_type(self, expr, scope_vars, line, scope_name):
        """Recursively infers the type of any expression."""
        expr_type = expr.get("type")

        if expr_type == "literal_scalar":
            return "scalar"
        if expr_type == "literal_boolean":
            return "boolean"
        if expr_type == "literal_vector":
            return "vector"
        if isinstance(expr, _StringLiteral):
            return "string"

        if isinstance(expr, Token):  # Variable reference
            var_name = str(expr)
            if var_name not in scope_vars:
                err_code = ErrorCode.UNDEFINED_VARIABLE_IN_FUNC if scope_name != "global" else ErrorCode.UNDEFINED_VARIABLE
                raise ValuaScriptError(err_code, line=line, name=var_name, func_name=scope_name)
            return scope_vars[var_name]["type"]

        if expr_type == "conditional_expression":
            cond_type = self._infer_expression_type(expr["condition"], scope_vars, line, scope_name)
            if cond_type != "boolean":
                raise ValuaScriptError(ErrorCode.IF_CONDITION_NOT_BOOLEAN, line=line, provided=cond_type)
            then_type = self._infer_expression_type(expr["then_expr"], scope_vars, line, scope_name)
            else_type = self._infer_expression_type(expr["else_expr"], scope_vars, line, scope_name)
            if then_type != else_type:
                raise ValuaScriptError(ErrorCode.IF_ELSE_TYPE_MISMATCH, line=line, then_type=str(then_type), else_type=str(else_type))
            return then_type

        if "function" in expr:  # Function call
            func_name = expr["function"]
            args = expr.get("args", [])
            signature = self.all_signatures.get(func_name)
            if not signature:
                raise ValuaScriptError(ErrorCode.UNKNOWN_FUNCTION, line=line, name=func_name)

            inferred_arg_types = [self._infer_expression_type(arg, scope_vars, line, scope_name) for arg in args]

            # Type check arguments
            if not signature.get("variadic"):
                if len(inferred_arg_types) != len(signature["arg_types"]):
                    raise ValuaScriptError(ErrorCode.ARGUMENT_COUNT_MISMATCH, line=line, name=func_name, expected=len(signature["arg_types"]), provided=len(inferred_arg_types))
                for i, (expected, actual) in enumerate(zip(signature["arg_types"], inferred_arg_types)):
                    if expected != "any" and expected != actual:
                        raise ValuaScriptError(ErrorCode.ARGUMENT_TYPE_MISMATCH, line=line, arg_num=i + 1, name=func_name, expected=expected, provided=actual)

            return_type_rule = signature["return_type"]
            return return_type_rule(inferred_arg_types) if callable(return_type_rule) else return_type_rule

        raise ValuaScriptError(f"Internal compiler error: Cannot infer type for expression: {expr}")

    def _check_for_recursive_calls(self):
        """Builds a call graph and detects cycles."""
        call_graph = {name: set() for name in self.all_user_functions}
        for func_name, func_def in self.all_user_functions.items():
            queue = deque(func_def["body"])
            while queue:
                item = queue.popleft()
                if isinstance(item, dict):
                    if "function" in item and item["function"] in self.all_user_functions:
                        call_graph[func_name].add(item["function"])
                    for value in item.values():
                        if isinstance(value, list):
                            queue.extend(value)
                        elif isinstance(value, dict):
                            queue.append(value)

        # Check for cycles
        path, visited = set(), set()

        def visit(node):
            path.add(node)
            visited.add(node)
            for neighbour in call_graph.get(node, []):
                if neighbour in path or (neighbour not in visited and visit(neighbour)):
                    return True
            path.remove(node)
            return False

        for node in self.all_user_functions:
            if node not in visited and visit(node):
                raise ValuaScriptError(ErrorCode.RECURSIVE_CALL_DETECTED, path=f"involving {node}")


def _promote_expressions_to_assignments(steps):
    """
    Transforms the AST by "lifting" nested function calls into temporary
    variable assignments. This simplifies the later compilation stages.
    """
    final_steps = []
    temp_var_count = 0

    def lift_recursive_helper(expression):
        nonlocal temp_var_count
        if not isinstance(expression, dict) or "function" not in expression:
            return expression

        # First, recurse and lift arguments
        lifted_args = [lift_recursive_helper(arg) for arg in expression.get("args", [])]
        modified_expr = {**expression, "args": lifted_args}

        # Now, check if the current expression itself needs lifting
        if expression.get("parent_is_arg", False):
            temp_var_count += 1
            temp_var_name = f"__temp_{temp_var_count}"

            # The lifted expression is now a top-level assignment
            lifted_step = {"type": "assignment", "result": temp_var_name, "expression": {k: v for k, v in modified_expr.items() if k != "parent_is_arg"}, "line": expression["line"]}
            final_steps.append(lifted_step)

            # It is replaced by a token referencing the new temporary variable
            return Token("CNAME", temp_var_name)

        return modified_expr

    def mark_children(expression, is_arg):
        if not isinstance(expression, dict):
            return
        expression["parent_is_arg"] = is_arg
        for arg in expression.get("args", []):
            mark_children(arg, True)
        if "condition" in expression:
            mark_children(expression["condition"], True)
            mark_children(expression["then_expr"], True)
            mark_children(expression["else_expr"], True)

    for step in steps:
        mark_children(step["expression"], False)
        final_steps.append({**step, "expression": lift_recursive_helper(step["expression"])})

    return final_steps


def inline_and_flatten_udfs(steps, analysis, all_user_functions):
    """
    Performs UDF inlining and flattens the execution flow into a simple
    list of assignments, using the pre-computed analysis for context.
    """
    call_count = {}
    inlined_steps = []

    def mangle(name, func_name, count):
        return f"__{func_name}_{count}__{name}"

    for step in steps:
        expr = step["expression"]
        if isinstance(expr, dict) and expr.get("function") in all_user_functions:
            func_name = expr["function"]
            func_def = all_user_functions[func_name]

            count = call_count.get(func_name, 0) + 1
            call_count[func_name] = count

            # 1. Create assignments for parameters
            for i, param in enumerate(func_def["params"]):
                inlined_steps.append(
                    {
                        "type": "assignment",
                        "result": mangle(param["name"], func_name, count),
                        "expression": expr["args"][i],
                        "line": step["line"],
                    }
                )

            # 2. Process and mangle the function body
            for body_step in func_def["body"]:
                if body_step["type"] == "return_statement":
                    # Create the final assignment to the original variable
                    inlined_steps.append(
                        {
                            "type": "assignment",
                            "result": step["result"],
                            "expression": body_step["value"],  # This value will be mangled in the next pass
                            "line": step["line"],
                        }
                    )
                else:
                    inlined_steps.append(body_step)  # Add body step to be mangled

            # 3. Mangle all variables within the just-added body steps
            for i in range(len(inlined_steps) - len(func_def["body"]), len(inlined_steps)):
                s = inlined_steps[i]

                # Mangle result
                if "result" in s:
                    s["result"] = mangle(s["result"], func_name, count)

                # Mangle expression side
                q = deque([s["expression"]])
                while q:
                    item = q.popleft()
                    if isinstance(item, Token) and item.type == "CNAME":
                        if item.value in analysis["udf_scopes"][func_name]["variables"]:
                            item.value = mangle(item.value, func_name, count)
                    elif isinstance(item, dict):
                        for k, v in item.items():
                            if isinstance(v, (dict, Token)):
                                q.append(v)
                            elif isinstance(v, list):
                                q.extend(v)
        else:
            inlined_steps.append(step)

    return _promote_expressions_to_assignments(inlined_steps)
