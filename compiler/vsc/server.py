import logging
import re
import os
import sys
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken

# --- Robust Path Setup ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    vsc_package_dir = os.path.dirname(current_dir)
    if vsc_package_dir not in sys.path:
        sys.path.insert(0, vsc_package_dir)
    from vsc.compiler import validate_valuascript
    from vsc.exceptions import ValuaScriptError
    from vsc.utils import format_lark_error
except ImportError as e:
    # Basic logging if imports fail, helpful for debugging setup
    log_file_path = os.path.join(os.path.expanduser("~"), "vsc_server_startup_error.log")
    with open(log_file_path, "w") as f:
        f.write(f"Failed to import VSC components. sys.path: {sys.path}\n")
        f.write(f"ImportError: {e}\n")
    sys.exit(1)

from pygls.server import LanguageServer
from lsprotocol.types import Diagnostic, Position, Range, DiagnosticSeverity

server = LanguageServer("valuascript-server", "v1")


def _validate(ls, params):
    text_doc = ls.workspace.get_document(params.text_document.uri)
    source = text_doc.source
    diagnostics = []

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def strip_ansi(text):
        return ansi_escape.sub("", text)

    try:
        # Single call to the unified validation function
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

    ls.publish_diagnostics(params.text_document.uri, diagnostics)


@server.feature("textDocument/didOpen")
async def did_open(ls, params):
    _validate(ls, params)


@server.feature("textDocument/didChange")
def did_change(ls, params):
    _validate(ls, params)


if __name__ == "__main__":
    server.start_io()
