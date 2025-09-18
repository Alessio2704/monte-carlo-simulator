import json
import argparse
import sys
import os
import time
from lark.exceptions import UnexpectedInput, UnexpectedCharacters
from vsc.compiler import compile_valuascript, CompilerArtifactEncoder
from vsc.exceptions import ValuaScriptError
from vsc.utils import TerminalColors, format_lark_error


def main():
    start_time = time.perf_counter()

    try:
        parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
        parser.add_argument("input_file", nargs="?", default=None, help="The path to the input .vs file. Omit to read from stdin.")
        parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file.")

        parser.add_argument(
            "-c",
            "--compile",
            type=str,
            choices=["1", "2", "3", "4", "5", "6a", "6", "7"],
            help="Compile up to a specific stage and save the intermediate artifact. "
            "1: AST, 2: Symbol Table, 3: Type Inference, 4: Semantic Validation, 5: IR, "
            "6a: Optimized IR (Phase 1), 6: Optimized IR (Final), 7: Recipe. "
            "Omitting this flag runs the full pipeline to generate the final .json file.",
        )
        # Other args...
        parser.add_argument("--lsp", action="store_true", help="Run the language server.")

        args = parser.parse_args()

        if args.lsp:
            from vsc.server import start_server

            start_server()
            return

        if not args.input_file and sys.stdin.isatty():
            parser.error("input_file is required when not reading from a pipe.")

        script_path_for_display = args.input_file or "stdin"
        print(f"--- Compiling {script_path_for_display} ---")

        try:
            if not args.input_file:
                script_content = sys.stdin.read()
                input_file_path_abs = None
            else:
                input_file_path_abs = os.path.abspath(args.input_file)
                with open(input_file_path_abs, "r") as f:
                    script_content = f.read()

            STAGE_MAP = {
                "1": "ast",
                "2": "symbol_table",
                "3": "type_inference",
                "4": "semantic_validation",
                "5": "ir",
                "6a": "copy_propagation",
                "6": "optimized_ir",
                "7": "recipe",
            }

            stop_after_stage = STAGE_MAP.get(args.compile)
            # Tell the pipeline which artifact to save to a file
            dump_stages = [stop_after_stage] if stop_after_stage else []

            final_product = compile_valuascript(script_content, file_path=input_file_path_abs, dump_stages=dump_stages, stop_after_stage=stop_after_stage)

            if not stop_after_stage:
                # This block runs for a full compilation
                raw_output_path = args.output_file or (os.path.splitext(args.input_file)[0] + ".json" if args.input_file else "stdin.json")
                output_file_path = os.path.abspath(raw_output_path)
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                with open(output_file_path, "w") as f:
                    f.write(json.dumps(final_product, indent=2, cls=CompilerArtifactEncoder))

                print(f"\n{TerminalColors.GREEN}--- Compilation Successful ---{TerminalColors.RESET}")
                print(f"Recipe written to {output_file_path}")
            else:
                # The pipeline already prints the "Artifact saved" message.
                print(f"\n{TerminalColors.GREEN}--- Compilation to stage '{args.compile} ({stop_after_stage})' successful ---{TerminalColors.RESET}")

        except (UnexpectedInput, UnexpectedCharacters) as e:
            script_content = script_content or ""
            print(format_lark_error(e, script_content), file=sys.stderr)
            sys.exit(1)
        except ValuaScriptError as e:
            print(f"\n{TerminalColors.RED}--- COMPILATION ERROR ---\n{e}{TerminalColors.RESET}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"{TerminalColors.RED}ERROR: Script file '{script_path_for_display}' not found.{TerminalColors.RESET}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\n{TerminalColors.RED}--- UNEXPECTED ERROR ---\n{type(e).__name__}: {e}{TerminalColors.RESET}", file=sys.stderr)
            sys.exit(1)

    finally:
        if "--lsp" not in sys.argv:
            end_time = time.perf_counter()
            duration = end_time - start_time
            print(f"\n{TerminalColors.CYAN}--- Total Execution Time: {duration:.4f} seconds ---{TerminalColors.RESET}")


if __name__ == "__main__":
    main()
