import { ExtensionContext } from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";

let client: LanguageClient;

export function activate(context: ExtensionContext) {
  console.log("--- ValuaScript Extension Activation ---");

  const command = "vsc";
  const serverArgs = ["--lsp"];

  const serverOptions: ServerOptions = {
    command: command,
    args: serverArgs,
    options: {},
  };

  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "valuascript" }],
  };

  client = new LanguageClient(
    "valuascriptLanguageServer",
    "ValuaScript Language Server",
    serverOptions,
    clientOptions
  );

  console.log(
    `Starting language server with command: ${command} ${serverArgs.join(" ")}`
  );
  client.start();
}

export function deactivate(): Thenable<void> | undefined {
  if (!client) {
    return undefined;
  }
  return client.stop();
}
