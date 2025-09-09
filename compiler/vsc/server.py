import re
import os
import sys
import subprocess
import json
import tempfile
from collections import deque
from urllib.parse import urlparse, unquote
from pathlib import Path
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken
from pygls.server import LanguageServer
from lsprotocol.types import (
    Diagnostic,
    Position,
    Range,
    DiagnosticSeverity,
    MarkupContent,
    MarkupKind,
    TEXT_DOCUMENT_HOVER,
    Hover,
    TEXT_DOCUMENT_DEFINITION,
    Location,
)
from pygls.workspace import Document

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vsc.compiler import compile_valuascript, resolve_imports_and_functions
from vsc.parser import parse_valuascript
from vsc.validator import validate_semantics
from vsc.optimizer import _build_dependency_graph, _find_stochastic_variables
from vsc.config import FUNCTION_SIGNATURES
from vsc.exceptions import ValuaScriptError
from vsc.utils import format_lark_error, find_engine_executable

server = LanguageServer("valuascript-server", "v1")


def _uri_to_path(uri: str) -> str:
    """Converts a file URI to a platform-specific file path."""
    parsed = urlparse(uri)
    return os.path.abspath(unquote(parsed.path))


def _path_to_uri(path: str) -> str:
    """Converts a platform-specific file path to a file URI."""
    return Path(path).as_uri()


def _format_number_with_separators(n):
    """Formats a number with underscores for thousands separation."""
    if isinstance(n, int):
        return f"{n:,}".replace(",", "_")
    if isinstance(n, float):
        parts = str(n).split(".")
        integer_part = f"{int(parts[0]):,}".replace(",", "_")
        return f"{integer_part}.{parts[1]}"
    return n


def _validate(ls, params):
    text_doc = ls.workspace.get_document(params.text_document.uri)
    source = text_doc.source
    diagnostics = []
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def strip_ansi(text):
        return ansi_escape.sub("", text)

    original_stdout = sys.stdout
    try:
        sys.stdout = open(os.devnull, "w")
        file_path = _uri_to_path(params.text_document.uri)
        compile_valuascript(source, context="lsp", file_path=file_path)
    except (UnexpectedInput, UnexpectedCharacters, UnexpectedToken) as e:
        line, col = e.line - 1, e.column - 1
        msg = strip_ansi(format_lark_error(e, source).splitlines()[-1])
        diagnostics.append(Diagnostic(range=Range(start=Position(line, col), end=Position(line, col + 100)), message=msg, severity=DiagnosticSeverity.Error))
    except ValuaScriptError as e:
        msg = strip_ansi(str(e))
        line = 0
        match = re.match(r"L(\d+):", msg)
        if match:
            line = int(match.group(1)) - 1
            msg = msg[len(match.group(0)) :].strip()
        diagnostics.append(Diagnostic(range=Range(start=Position(line, 0), end=Position(line, 100)), message=msg, severity=DiagnosticSeverity.Error))
    finally:
        sys.stdout.close()
        sys.stdout = original_stdout
    ls.publish_diagnostics(params.text_document.uri, diagnostics)


@server.feature("textDocument/didOpen")
async def did_open(ls, params):
    _validate(ls, params)


@server.feature("textDocument/didChange")
def did_change(ls, params):
    _validate(ls, params)


def _get_word_at_position(document: Document, position: Position) -> str:
    line = document.lines[position.line]
    start, end = position.character, position.character
    while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
        start -= 1
    while end < len(line) and (line[end].isalnum() or line[end] == "_"):
        end += 1
    return line[start:end]


def _is_udf_stochastic(func_def, user_functions, checked_functions=None):
    if checked_functions is None:
        checked_functions = set()
    if func_def["name"] in checked_functions:
        return False

    checked_functions.add(func_def["name"])

    for item in func_def.get("body", []):
        queue = deque([item])
        while queue:
            current = queue.popleft()
            if isinstance(current, dict):
                func_name = current.get("function")
                if func_name and FUNCTION_SIGNATURES.get(func_name, {}).get("is_stochastic"):
                    return True
                if func_name in user_functions:
                    if _is_udf_stochastic(user_functions[func_name], user_functions, checked_functions):
                        return True
                for value in current.values():
                    if isinstance(value, list):
                        queue.extend(value)
                    elif isinstance(value, dict):
                        queue.append(value)
    return False


def _get_script_analysis(source: str, file_path: str):
    """
    Performs a partial compilation to get semantic info needed for hover tooltips.
    """
    try:
        high_level_ast = parse_valuascript(source)
        all_user_functions_with_meta = resolve_imports_and_functions(high_level_ast, file_path)
        all_user_function_defs = {k: v["definition"] for k, v in all_user_functions_with_meta.items()}

        inlined_steps, defined_vars, _, _ = validate_semantics(high_level_ast, all_user_function_defs, is_preview_mode=True)
        _, dependents = _build_dependency_graph(inlined_steps)
        stochastic_vars = _find_stochastic_variables(inlined_steps, dependents)

        # The server needs the metadata (source path), so we return the full map.
        return defined_vars, stochastic_vars, all_user_functions_with_meta
    except Exception:
        return {}, set(), {}


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(params):
    document = server.workspace.get_document(params.text_document.uri)
    word = _get_word_at_position(document, params.position)
    source = document.source
    file_path = _uri_to_path(params.text_document.uri)
    defined_vars, stochastic_vars, user_functions_with_meta = _get_script_analysis(source, file_path)
    user_functions = {k: v["definition"] for k, v in user_functions_with_meta.items()}

    if word in FUNCTION_SIGNATURES:
        sig = FUNCTION_SIGNATURES[word]
        doc = sig.get("doc")
        if not doc:
            return None
        param_names = [p["name"] for p in doc.get("params", [])]
        signature_str = f"{word}({', '.join(param_names)})"
        contents = [f"```valuascript\n(function) {signature_str}\n```", "---", f"**{doc.get('summary', '')}**"]
        if "params" in doc and doc["params"]:
            param_docs = ["\n#### Parameters:"]
            for p in doc["params"]:
                param_docs.append(f"- `{p.get('name', '')}`: {p.get('desc', '')}")
            contents.append("\n".join(param_docs))
        if "returns" in doc:
            returns_doc = doc.get("returns", "")
            return_type_val = sig.get("return_type", "any")
            return_type_str = "dynamic" if callable(return_type_val) else return_type_val
            contents.append(f"\n**Returns**: `{return_type_str}` — {returns_doc}")
        return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value="\n".join(contents)))

    if word in user_functions:
        func_def = user_functions[word]
        params_str = ", ".join([f"{p['name']}: {p['type']}" for p in func_def["params"]])
        signature = f"(user defined function) {func_def['name']}({params_str}) -> {func_def['return_type']}"
        contents = [f"```valuascript\n{signature}\n```"]
        if func_def.get("docstring"):
            contents.append("---")
            contents.append(func_def["docstring"])
        return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value="\n".join(contents)))

    if word in defined_vars:
        var_info = defined_vars[word]
        var_type = var_info.get("type", "unknown")

        if var_type == "error":
            header = f"```valuascript\n(variable) {word}: error\n```"
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"{header}\n\n---\n*This line contains an error. Cannot compute value.*"))

        is_stochastic = word in stochastic_vars
        kind = "stochastic" if is_stochastic else "deterministic"
        header = f"```valuascript\n(variable) {word}: {var_type} ({kind})\n```"

        tmp_recipe_file = None
        try:
            recipe = compile_valuascript(source, context="lsp", preview_variable=word, file_path=file_path)
            engine_path = find_engine_executable(None)

            if not engine_path:
                return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"{header}\n\n---\n*Error: Simulation engine 'vse' not found.*"))

            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_recipe_file:
                json.dump(recipe, tmp_recipe_file)
                recipe_path = tmp_recipe_file.name

            run_proc = subprocess.run([engine_path, "--preview", recipe_path], text=True, capture_output=True, timeout=15)

            if run_proc.stdout:
                try:
                    result_json = json.loads(run_proc.stdout)
                    if result_json.get("status") == "error":
                        message = result_json.get("message", "An unknown error occurred in the engine.")
                        return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"{header}\n\n---\n*Engine Runtime Error:*\n```\n{message}\n```"))
                except json.JSONDecodeError:
                    pass

            if run_proc.returncode != 0:
                error_output = run_proc.stderr.strip() or "Process failed without an error message."
                return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"{header}\n\n---\n*Error during value preview:*\n```\n{error_output}\n```"))

            try:
                result_json = json.loads(run_proc.stdout)
            except json.JSONDecodeError:
                return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"{header}\n\n---\n*Error: Could not parse preview result from engine.*"))

            value = result_json.get("value")
            value_label = "Mean Value (100 trials)" if is_stochastic else "Value"

            formatted_value = value
            if isinstance(value, bool):
                formatted_value = "True" if value is True else "False"
            elif isinstance(value, (int, float)):
                formatted_value = _format_number_with_separators(value)
            elif isinstance(value, list):
                formatted_value = [_format_number_with_separators(item) for item in value]

            value_str = json.dumps(formatted_value, indent=2)
            # Perform the replacement outside the f-string for compatibility with Python < 3.12
            clean_value_str = value_str.replace('"', "")
            md_value = f"**{value_label}:**\n```\n{clean_value_str}\n```"
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"{header}\n\n---\n{md_value}"))
        except Exception as e:
            return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=f"{header}\n\n---\n*An error occurred while fetching live value: {e}*"))
        finally:
            if tmp_recipe_file and os.path.exists(tmp_recipe_file.name):
                os.remove(tmp_recipe_file.name)

    return None


@server.feature(TEXT_DOCUMENT_DEFINITION)
def definition(params):
    document = server.workspace.get_document(params.text_document.uri)
    word = _get_word_at_position(document, params.position)

    if not word:
        return None

    source = document.source
    file_path = _uri_to_path(params.text_document.uri)
    _, _, user_functions_with_meta = _get_script_analysis(source, file_path)

    if word in user_functions_with_meta:
        func_meta = user_functions_with_meta[word]
        func_def = func_meta["definition"]
        source_path = func_meta["source_path"]

        if not source_path:
            return None

        # The line number from the parser is 1-based.
        line = func_def.get("line", 1) - 1

        return Location(uri=_path_to_uri(source_path), range=Range(start=Position(line, 0), end=Position(line, 100)))

    return None


def start_server():
    server.start_io()


if __name__ == "__main__":
    start_server()
