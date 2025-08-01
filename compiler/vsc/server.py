import re
import os
import sys
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken
from pygls.server import LanguageServer
from lsprotocol.types import Diagnostic, Position, Range, DiagnosticSeverity
from lsprotocol.types import (
    TEXT_DOCUMENT_HOVER,
    Hover,
    MarkupContent,
    MarkupKind,
    Position,
)
from pygls.workspace import Document
from vsc.config import FUNCTION_SIGNATURES

# Ensure the server can find its own modules when packaged
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from vsc.compiler import validate_valuascript
from vsc.exceptions import ValuaScriptError
from vsc.utils import format_lark_error

server = LanguageServer("valuascript-server", "v1")


def _validate(ls, params):
    text_doc = ls.workspace.get_document(params.text_document.uri)
    source = text_doc.source
    diagnostics = []

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def strip_ansi(text):
        return ansi_escape.sub("", text)

    original_stdout = sys.stdout
    try:
        # Redirect stdout to a null device to suppress any print() statements
        # from the validation function, which would corrupt the LSP stream.
        sys.stdout = open(os.devnull, "w")

        # Single call to the unified validation function with the LSP context
        validate_valuascript(source, context="lsp")

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
        # Always restore stdout, even if an error occurred.
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
    """Helper to get the word under the cursor."""
    line = document.lines[position.line]
    start, end = position.character, position.character
    while start > 0 and line[start - 1].isidentifier():
        start -= 1
    while end < len(line) and line[end].isidentifier():
        end += 1
    return line[start:end]


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(params):
    """Handler for the hover feature."""
    document = server.workspace.get_document(params.text_document.uri)
    word = _get_word_at_position(document, params.position)

    if word in FUNCTION_SIGNATURES:
        sig = FUNCTION_SIGNATURES[word]
        doc = sig.get("doc")
        if not doc:
            return None

        # Build the function signature string
        param_names = [p["name"] for p in doc.get("params", [])]
        signature_str = f"{word}({', '.join(param_names)})"

        # Build the documentation content in Markdown
        contents = [
            f"```valuascript\n(function) {signature_str}\n```",
            "---",
            f"**{doc.get('summary', '')}**",
        ]

        if "params" in doc and doc["params"]:
            param_docs = ["\n#### Parameters:"]
            for p in doc["params"]:
                param_docs.append(f"- `{p.get('name', '')}`: {p.get('desc', '')}")
            contents.append("\n".join(param_docs))

        if "returns" in doc:
            contents.append(f"\n**Returns**: `{sig.get('return_type', 'any')}` — {doc.get('returns', '')}")

        return Hover(contents=MarkupContent(kind=MarkupKind.Markdown, value="\n".join(contents)))

    return None


def start_server():
    server.start_io()


if __name__ == "__main__":
    start_server()
