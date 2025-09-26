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
    TEXT_DOCUMENT_COMPLETION,
    CompletionItem,
    CompletionList,
    CompletionItemKind,
    InsertTextFormat,
)
from pygls.workspace import Document

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vsc.compiler import compile_valuascript, resolve_imports_and_functions
from vsc.parser.parser import parse_valuascript
from vsc.validator import SemanticAnalyzer
from vsc.optimizer import _build_dependency_graph, _find_stochastic_variables
from vsc.functions import FUNCTION_SIGNATURES
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

    try:
        file_path = _uri_to_path(params.text_document.uri)
        # Run the full compilation pipeline to get validation errors
        compile_valuascript(source, context="lsp", file_path=file_path)
    except (UnexpectedInput, UnexpectedCharacters, UnexpectedToken) as e:
        line, col = e.line - 1, e.column - 1
        msg = strip_ansi(format_lark_error(e, source).splitlines()[-1])
        diagnostics.append(Diagnostic(range=Range(start=Position(line, col), end=Position(line, col + 100)), message=msg, severity=DiagnosticSeverity.Error))
    except ValuaScriptError as e:
        msg = strip_ansi(str(e))
        line = e.line - 1 if e.line > 0 else 0
        diagnostics.append(Diagnostic(range=Range(start=Position(line, 0), end=Position(line, 100)), message=msg, severity=DiagnosticSeverity.Error))
    except Exception:
        # Catch-all for other unexpected errors during validation
        pass

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


def _get_script_analysis(source: str, file_path: str):
    """
    Performs a full, deep analysis of the script and its imports, returning
    the rich symbol table structure. Returns None on syntax error.
    """
    try:
        main_ast = parse_valuascript(source)
        all_user_functions = resolve_imports_and_functions(main_ast, file_path)
        analyzer = SemanticAnalyzer(main_ast, all_user_functions, file_path)
        return analyzer.analyze(), all_user_functions, main_ast
    except (ValuaScriptError, UnexpectedInput, UnexpectedCharacters, UnexpectedToken):
        return None, {}, None


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(params):
    document = server.workspace.get_document(params.text_document.uri)
    word = _get_word_at_position(document, params.position)
    source = document.source
    file_path = _uri_to_path(params.text_document.uri)

    analysis, all_user_functions, _ = _get_script_analysis(source, file_path)
    if not analysis:
        return None

    # --- Hover for Built-in Function ---
    if word in FUNCTION_SIGNATURES:
        sig = FUNCTION_SIGNATURES[word]
        doc = sig.get("doc")
        if not doc:
            return None
        param_names = [p["name"] for p in doc.get("params", [])]
        signature_str = f"{word}({', '.join(param_names)})"
        contents = [f"```valuascript\n(function) {signature_str}\n```", "---", f"**{doc.get('summary', '')}**"]
        return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value="\n".join(contents)))

    # --- Hover for User-Defined Function ---
    if word in all_user_functions:
        func_def = all_user_functions[word]
        params_str = ", ".join([f"{p['name']}: {p['type']}" for p in func_def["params"]])
        return_str = str(func_def["return_type"])
        signature = f"(user defined function) {func_def['name']}({params_str}) -> {return_str}"
        contents = [f"```valuascript\n{signature}\n```"]
        if func_def.get("docstring"):
            contents.extend(["---", func_def["docstring"]])
        return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value="\n".join(contents)))

    # --- Hover for Variable (needs context) ---
    # This part is complex because a variable name can exist in multiple scopes.
    # A full implementation would find the specific scope of the cursor.
    # For now, we check global scope as a priority.
    if word in analysis["global_scope"]["variables"]:
        var_info = analysis["global_scope"]["variables"][word]
        var_type = var_info.get("type", "unknown")
        header = f"```valuascript\n(variable) {word}: {var_type}\n```"
        return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value=header))

    return None


@server.feature(TEXT_DOCUMENT_DEFINITION)
def definition(params):
    document = server.workspace.get_document(params.text_document.uri)
    word = _get_word_at_position(document, params.position)
    if not word:
        return None

    source = document.source
    file_path = _uri_to_path(params.text_document.uri)
    _, all_user_functions, _ = _get_script_analysis(source, file_path)

    if word in all_user_functions:
        func_def = all_user_functions[word]
        source_path = func_def.get("source_path")
        if not source_path:
            return None
        line = func_def.get("line", 1) - 1
        return Location(uri=_path_to_uri(source_path), range=Range(start=Position(line, 0), end=Position(line, 100)))

    return None


def _create_function_snippet(name: str, params: list) -> str:
    """Creates an LSP snippet string from a function name and parameter list."""
    placeholders = [f"${{{i+1}:{p['name']}}}" for i, p in enumerate(params)]
    return f"{name}({', '.join(placeholders)})" if placeholders else f"{name}()"


@server.feature(TEXT_DOCUMENT_COMPLETION)
def completions(params):
    document = server.workspace.get_document(params.text_document.uri)
    source = document.source
    file_path = _uri_to_path(params.text_document.uri)
    cursor_pos = params.position

    analysis, all_user_functions, ast = _get_script_analysis(source, file_path)
    if not analysis:
        return CompletionList(items=[], is_incomplete=False)

    completion_items = []

    # --- Add Global Symbols ---
    # Built-in functions
    for name, sig in FUNCTION_SIGNATURES.items():
        if not name.startswith("__"):
            snippet = _create_function_snippet(name, sig.get("doc", {}).get("params", []))
            completion_items.append(
                CompletionItem(
                    label=name,
                    kind=CompletionItemKind.Function,
                    detail="Built-in Function",
                    documentation=sig.get("doc", {}).get("summary"),
                    insert_text=snippet,
                    insert_text_format=InsertTextFormat.Snippet,
                )
            )

    # All UDFs are global
    for name, func_def in all_user_functions.items():
        source_file = os.path.basename(func_def.get("source_path", "unknown file"))
        snippet = _create_function_snippet(name, func_def.get("params", []))
        completion_items.append(
            CompletionItem(
                label=name,
                kind=CompletionItemKind.Function,
                detail=f"User-Defined Function in {source_file}",
                documentation=func_def.get("docstring"),
                insert_text=snippet,
                insert_text_format=InsertTextFormat.Snippet,
            )
        )

    # Global variables
    for name, info in analysis["global_scope"]["variables"].items():
        completion_items.append(CompletionItem(label=name, kind=CompletionItemKind.Variable, detail=f"Variable ({info.get('type', 'unknown')})"))

    # --- Add UDF-Scoped Symbols if inside a function ---
    if ast:
        for func_def in ast.get("function_definitions", []):
            start_line = func_def.get("line", 0) - 1
            # Find the line of the closing brace '}' to define the scope boundary
            # This is tricky without a full parser context, so we approximate
            # by finding the line of the last statement in the function body.
            end_line = start_line
            if func_def.get("body"):
                last_statement = func_def["body"][-1]
                end_line = last_statement.get("line", start_line + 1)

            if start_line <= cursor_pos.line <= end_line + 1:
                scope_name = func_def["name"]
                udf_scope = analysis["udf_scopes"].get(scope_name)
                if udf_scope:
                    # Add parameters
                    for param in udf_scope.get("params", []):
                        completion_items.append(CompletionItem(label=param["name"], kind=CompletionItemKind.Variable, detail=f"Parameter ({param['type']})"))

                    # Add local variables defined *before* the cursor
                    for var_name, var_info in udf_scope.get("variables", {}).items():
                        if var_info["line"] - 1 < cursor_pos.line:
                            completion_items.append(CompletionItem(label=var_name, kind=CompletionItemKind.Variable, detail=f"Local Variable ({var_info.get('type')})"))
                break  # Found the scope, no need to check other functions

    return CompletionList(items=completion_items, is_incomplete=False)


def start_server():
    server.start_io()


if __name__ == "__main__":
    start_server()
