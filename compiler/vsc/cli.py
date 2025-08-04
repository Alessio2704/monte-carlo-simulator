import json
import argparse
import sys
import os
import subprocess
import time
from lark.exceptions import UnexpectedInput, UnexpectedCharacters, UnexpectedToken

try:
    # This must be the first import to set up the path correctly
    from .compiler import validate_valuascript
    from .exceptions import ValuaScriptError
    from .utils import TerminalColors, format_lark_error, find_engine_executable, generate_and_show_plot
except ImportError:
    # If run directly, this might fail, so we add the parent dir to the path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from vsc.compiler import validate_valuascript
    from vsc.exceptions import ValuaScriptError
    from vsc.utils import TerminalColors, format_lark_error, find_engine_executable, generate_and_show_plot


def main():
    start_time = time.perf_counter()

    try:
        parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
        parser.add_argument("input_file", nargs="?", default=None, help="The path to the input .vs file.")
        parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file.")
        parser.add_argument("--run", action="store_true", help="Execute the simulation engine after a successful compilation.")
        parser.add_argument("--plot", action="store_true", help="Generate and display a histogram of the simulation results.")
        parser.add_argument("--engine-path", help="Explicit path to the 'vse' executable.")
        parser.add_argument("--lsp", action="store_true", help="Run the language server.")
        args = parser.parse_args()

        if args.lsp:
            from vsc.server import start_server

            start_server()
            return

        if not args.input_file:
            parser.error("the following arguments are required: input_file")

        output_file_path = args.output_file or os.path.splitext(args.input_file)[0] + ".json"
        script_path = args.input_file

        try:
            with open(script_path, "r") as f:
                script_content = f.read()

            print(f"--- Compiling {script_path} -> {output_file_path} ---")
            final_recipe = validate_valuascript(script_content)

            with open(output_file_path, "w") as f:
                f.write(json.dumps(final_recipe, indent=2))

            print(f"\n{TerminalColors.GREEN}--- Compilation Successful ---{TerminalColors.RESET}")
            print(f"Recipe written to {output_file_path}")

            if args.run:
                engine_executable = find_engine_executable(args.engine_path)
                if not engine_executable:
                    print(f"\n{TerminalColors.RED}--- Execution Failed: Could not find the simulation engine. ---{TerminalColors.RESET}", file=sys.stderr)
                    sys.exit(1)

                print(f"\n--- Running Simulation ---")
                subprocess.run([engine_executable, output_file_path], check=True)
                print(f"{TerminalColors.GREEN}--- Simulation Finished Successfully ---{TerminalColors.RESET}")

                if args.plot:
                    output_file_from_recipe = final_recipe.get("simulation_config", {}).get("output_file")
                    if output_file_from_recipe and os.path.exists(output_file_from_recipe):
                        generate_and_show_plot(output_file_from_recipe)

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
        if "--lsp" not in sys.argv:
            end_time = time.perf_counter()
            duration = end_time - start_time
            print(f"\n{TerminalColors.CYAN}--- Total Execution Time: {duration:.4f} seconds ---{TerminalColors.RESET}")
