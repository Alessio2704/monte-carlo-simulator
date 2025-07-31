import re
import os
import sys
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken
from pygls.server import LanguageServer
from lsprotocol.types import Diagnostic, Position, Range, DiagnosticSeverity

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
        # --- THE FIX ---
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
        # --- THE FIX ---
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


def start_server():
    server.start_io()


if __name__ == "__main__":
    start_server()
