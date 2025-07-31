import * as path from "path";
import { workspace, ExtensionContext } from "vscode";
import * as fs from "fs"; // Import the file system module
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";

let client: LanguageClient;

export function activate(context: ExtensionContext) {
  console.log("--- ValuaScript Extension Activation ---");

  // Construct the absolute path to the virtual environment's Python executable
  const pythonExecutable =
    process.platform === "win32" ? "python.exe" : "python";
  const pythonPath = context.asAbsolutePath(
    path.join("..", "compiler", "venv", "bin", pythonExecutable)
  );

  // --- CRITICAL DIAGNOSTIC STEP ---
  // Check if the Python executable actually exists before trying to use it.
  if (!fs.existsSync(pythonPath)) {
    const errorMsg = `FATAL: Python executable not found at the expected path: ${pythonPath}. Please ensure the virtual environment exists in 'compiler/venv'.`;
    console.error(errorMsg);
    // Show an error message to the user
    import("vscode").then((vscode) => {
      vscode.window.showErrorMessage(errorMsg);
    });
    return; // Stop activation if Python is not found
  }

  console.log(`Found Python executable at: ${pythonPath}`);

  const serverModule = context.asAbsolutePath(
    path.join("..", "compiler", "vsc", "server.py")
  );

  const serverOptions: ServerOptions = {
    command: pythonPath,
    args: [serverModule],
    options: {},
  };

  // --- DIAGNOSTIC LOG ---
  console.log(`Server command: ${serverOptions.command}`);
  console.log(`Server args: ${JSON.stringify(serverOptions.args)}`);

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "valuascript" }],
  };

  client = new LanguageClient(
    "valuascriptLanguageServer",
    "ValuaScript Language Server",
    serverOptions,
    clientOptions
  );

  console.log("Starting ValuaScript Language Server...");
  client.start().catch((error) => {
    // --- DIAGNOSTIC LOG ---
    // Log if the client fails to start for any reason.
    console.error(`Language Client failed to start: ${error}`);
  });
  console.log("Language client start initiated.");
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  console.log("Stopping ValuaScript Language Server...");
  return client.stop();
}
