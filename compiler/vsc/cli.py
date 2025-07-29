# compiler/vsc/cli.py

"""
Command-line interface for the ValuaScript compiler.
Parses arguments, orchestrates the compilation and execution process.
"""

import json
import argparse
import sys
import os
import subprocess
from lark import Lark
from lark.exceptions import UnexpectedInput, UnexpectedCharacters

# --- NEW: Use modern library for package data access ---
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Fallback for Python < 3.7
    import importlib_resources as pkg_resources


from .compiler import ValuaScriptTransformer, validate_recipe, lint_script
from .exceptions import ValuaScriptError
from .utils import TerminalColors, format_lark_error, find_engine_executable, generate_and_show_plot


def main():
    parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
    parser.add_argument("input_file", help="The path to the input .vs file.")
    parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file.")
    parser.add_argument("--run", action="store_true", help="Execute the simulation engine after a successful compilation.")
    parser.add_argument("--plot", action="store_true", help="Generate and display a histogram of the simulation results. Requires --run and an @output_file directive.")
    parser.add_argument("--engine-path", help="Explicit path to the 'monte-carlo-simulator' executable.")
    args = parser.parse_args()

    output_file_path = args.output_file or os.path.splitext(args.input_file)[0] + ".json"
    script_path = args.input_file
    print(f"--- Compiling {script_path} -> {output_file_path} ---")

    try:
        # --- ROBUST WAY TO GET GRAMMAR ---
        # This will work whether running from source or as an installed package.
        with pkg_resources.path("vsc", "..") as p:
            grammar_path = os.path.join(p, "valuascript.lark")
            with open(grammar_path, "r") as f:
                valuasc_grammar = f.read()

    except Exception as e:
        print(f"{TerminalColors.RED}FATAL ERROR: Could not load internal grammar file 'valuascript.lark': {e}{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)

    lark_parser = Lark(valuasc_grammar, start="start", parser="earley")
    script_content = ""
    try:
        with open(script_path, "r") as f:
            script_content = f.read()
        lint_script(script_content)
        parse_tree = lark_parser.parse(script_content)
        raw_recipe = ValuaScriptTransformer().transform(parse_tree)
        final_recipe = validate_recipe(raw_recipe)

        with open(output_file_path, "w") as f:
            f.write(json.dumps(final_recipe, indent=2))

        print(f"\n{TerminalColors.GREEN}--- Compilation Successful ---{TerminalColors.RESET}")
        print(f"Recipe written to {output_file_path}")

        if args.run:
            engine_executable = find_engine_executable(args.engine_path)
            if not engine_executable:
                print(f"\n{TerminalColors.RED}--- Execution Failed ---\nCould not find 'monte-carlo-simulator'.{TerminalColors.RESET}", file=sys.stderr)
                sys.exit(1)

            print(f"\n--- Running Simulation ---")
            result = subprocess.run([engine_executable, output_file_path], capture_output=False, text=True)

            if result.returncode == 0:
                print(f"{TerminalColors.GREEN}--- Simulation Finished Successfully ---{TerminalColors.RESET}")
                if args.plot:
                    print("\n--- Generating Plot ---")
                    output_file_from_recipe = final_recipe.get("simulation_config", {}).get("output_file")
                    if not output_file_from_recipe:
                        print(f"{TerminalColors.YELLOW}Warning: Cannot plot. The --plot flag requires the @output_file directive in your .vs file.{TerminalColors.RESET}", file=sys.stderr)
                    elif not os.path.exists(output_file_from_recipe):
                        print(f"{TerminalColors.YELLOW}Warning: Cannot plot. Output file '{output_file_from_recipe}' was not found.{TerminalColors.RESET}", file=sys.stderr)
                    else:
                        generate_and_show_plot(output_file_from_recipe)
            else:
                print(f"{TerminalColors.RED}--- Simulation Failed (Exit Code: {result.returncode}) ---{TerminalColors.RESET}", file=sys.stderr)
                sys.exit(result.returncode)

    except (UnexpectedInput, UnexpectedCharacters) as e:
        print(format_lark_error(e, script_content), file=sys.stderr)
        sys.exit(1)
    except ValuaScriptError as e:
        print(f"\n{TerminalColors.RED}--- SEMANTIC ERROR ---\n{e}{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"{TerminalColors.RED}ERROR: Script file '{script_path}' not found.{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n{TerminalColors.RED}--- UNEXPECTED COMPILER ERROR ---\n{type(e).__name__}: {e}{TerminalColors.RESET}", file=sys.stderr)
        sys.exit(1)
