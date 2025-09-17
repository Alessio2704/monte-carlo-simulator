import json
import argparse
import sys
import os
import subprocess
import time
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken

try:
    # This must be the first import to set up the path correctly
    from .compiler import compile_valuascript
    from .exceptions import ValuaScriptError
    from .utils import TerminalColors, format_lark_error, find_engine_executable, generate_and_show_plot
except ImportError:
    # If run directly, this might fail, so we add the parent dir to the path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from vsc.compiler import compile_valuascript
    from vsc.exceptions import ValuaScriptError
    from vsc.utils import TerminalColors, format_lark_error, find_engine_executable, generate_and_show_plot


def main():
    start_time = time.perf_counter()

    try:
        parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
        parser.add_argument("input_file", nargs="?", default=None, help="The path to the input .vs file. Omit to read from stdin.")
        parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file.")

        parser.add_argument(
            "-c",
            "--compile",
            type=int,
            choices=[1, 2, 3, 4, 5, 6, 7],
            help="Compile up to a specific stage and save the intermediate artifact. "
            "1: AST, 2: Symbol Table, 3: Type Inference, 4: Semantic Model, 5: IR, 6: Optimized IR, 7: Recipe. "  # <-- UPDATED HELP TEXT
            "Omitting this flag runs the full pipeline to generate the final .json file.",
        )

        parser.add_argument("--run", action="store_true", help="Execute the simulation engine after a successful compilation.")
        parser.add_argument("--plot", action="store_true", help="Generate and display a histogram of the simulation results.")
        parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output during compilation.")
        parser.add_argument("--engine-path", help="Explicit path to the 'vse' executable.")
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
                1: "ast",
                2: "symbol_table",
                3: "type_inference",
                4: "semantic_model",
                5: "ir",
                6: "optimized_ir",
                7: "recipe",
            }

            stop_after_stage = STAGE_MAP.get(args.compile)

            # If we are stopping at a specific stage, we want to dump that artifact.
            dump_stages = [stop_after_stage] if stop_after_stage else []

            final_product = compile_valuascript(script_content, file_path=input_file_path_abs, dump_stages=dump_stages, stop_after_stage=stop_after_stage)

            # If we are not stopping early, then proceed to save the final recipe.
            if not stop_after_stage:
                raw_output_path = args.output_file or os.path.splitext(args.input_file)[0] + ".json" if args.input_file else "stdin.json"
                output_file_path = os.path.abspath(raw_output_path)
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                with open(output_file_path, "w") as f:
                    f.write(json.dumps(final_product, indent=2))

                print(f"\n{TerminalColors.GREEN}--- Compilation Successful ---{TerminalColors.RESET}")
                print(f"Recipe written to {output_file_path}")
            else:
                print(f"\n{TerminalColors.GREEN}--- Compilation to stage '{stop_after_stage}' successful ---{TerminalColors.RESET}")

        except (UnexpectedInput, UnexpectedCharacters, UnexpectedToken) as e:
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
