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
        parser.add_argument("--run", action="store_true", help="Execute the simulation engine after a successful compilation.")
        parser.add_argument("--plot", action="store_true", help="Generate and display a histogram of the simulation results.")
        parser.add_argument("-O", "--optimize", action="store_true", help="Enable aggressive optimizations like Dead Code Elimination.")
        parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output during compilation.")
        parser.add_argument("--engine-path", help="Explicit path to the 'vse' executable.")
        parser.add_argument("--lsp", action="store_true", help="Run the language server.")
        parser.add_argument("--preview-var", dest="preview_var", default=None, help="Generate a temporary recipe to preview a specific variable's value.")
        args = parser.parse_args()

        if args.lsp:
            from vsc.server import start_server

            start_server()
            return

        is_preview_mode = args.preview_var is not None

        if not args.input_file and sys.stdin.isatty() and not is_preview_mode:
            parser.error("input_file is required when not reading from a pipe or in preview mode.")

        # Determine the absolute path for the output file
        raw_output_path = args.output_file or os.path.splitext(args.input_file)[0] + ".json" if args.input_file else "stdin.json"
        output_file_path = os.path.abspath(raw_output_path)

        script_path = args.input_file or "stdin"

        try:
            if not args.input_file:
                script_content = sys.stdin.read()
                # When reading from stdin, file_path should be None to prevent import errors
                input_file_path_abs = None
            else:
                input_file_path_abs = os.path.abspath(args.input_file)
                with open(input_file_path_abs, "r") as f:
                    script_content = f.read()

            if not is_preview_mode:
                print(f"--- Compiling {script_path} -> {output_file_path} ---")

            final_recipe = compile_valuascript(
                script_content,
                optimize=args.optimize,
                verbose=args.verbose and not is_preview_mode,
                preview_variable=args.preview_var,
                file_path=input_file_path_abs,
            )

            # Ensure the output directory exists before writing the recipe
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

            with open(output_file_path, "w") as f:
                f.write(json.dumps(final_recipe, indent=2))

            if not is_preview_mode:
                print(f"\n{TerminalColors.GREEN}--- Compilation Successful ---{TerminalColors.RESET}")
                print(f"Recipe written to {output_file_path}")

            if args.run:
                engine_executable = find_engine_executable(args.engine_path)
                if not engine_executable:
                    print(f"\n{TerminalColors.RED}--- Execution Failed: Could not find the simulation engine. ---{TerminalColors.RESET}", file=sys.stderr)
                    sys.exit(1)

                # The engine's working directory should be where the recipe is,
                # so that relative paths in @output_file are handled correctly.
                engine_cwd = os.path.dirname(output_file_path)

                # We pass the absolute path of the recipe to the engine.
                command_args = [engine_executable, output_file_path]
                if is_preview_mode:
                    command_args.insert(1, "--preview")
                    proc = subprocess.run(command_args, capture_output=True, text=True, check=True, cwd=engine_cwd)
                    print(proc.stdout, end="")
                else:
                    print(f"\n--- Running Simulation ---")
                    subprocess.run(command_args, check=True, cwd=engine_cwd)
                    print(f"{TerminalColors.GREEN}--- Simulation Finished Successfully ---{TerminalColors.RESET}")

                if args.plot and not is_preview_mode:
                    output_file_from_recipe = final_recipe.get("simulation_config", {}).get("output_file")
                    if output_file_from_recipe:
                        # Construct the full path to the output file relative to the engine's CWD
                        full_output_path = os.path.join(engine_cwd, output_file_from_recipe)
                        if os.path.exists(full_output_path):
                            generate_and_show_plot(full_output_path)

        except (UnexpectedInput, UnexpectedCharacters, UnexpectedToken) as e:
            script_content = script_content or ""
            print(format_lark_error(e, script_content), file=sys.stderr)
            sys.exit(1)
        except ValuaScriptError as e:
            print(f"\n{TerminalColors.RED}--- COMPILATION ERROR ---\n{e}{TerminalColors.RESET}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print(f"{TerminalColors.RED}ERROR: Script file '{script_path}' not found.{TerminalColors.RESET}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"\n{TerminalColors.RED}--- UNEXPECTED ERROR ---\n{type(e).__name__}: {e}{TerminalColors.RESET}", file=sys.stderr)
            sys.exit(1)

    finally:
        if "--lsp" not in sys.argv and "--preview-var" not in sys.argv:
            end_time = time.perf_counter()
            duration = end_time - start_time
            print(f"\n{TerminalColors.CYAN}--- Total Execution Time: {duration:.4f} seconds ---{TerminalColors.RESET}")
