import json
import argparse
import sys
import os
import time
from lark.exceptions import UnexpectedInput, UnexpectedCharacters
from .compiler import compile_valuascript, CompilerArtifactEncoder
from .exceptions import ValuaScriptError
from .utils import TerminalColors, format_lark_error


def main():
    start_time = time.perf_counter()

    # This provides a single source of truth for stage names and their order.
    STAGE_MAP = {
        "1": ("ast", "Abstract Syntax Tree"),
        "2": ("symbol_table", "Symbol Table"),
        "3": ("type_inference", "Enriched Symbol Table (Types & Tainting)"),
        "4": ("semantic_validation", "Validated Semantic Model"),
        "5": ("ir", "Initial Intermediate Representation (IR)"),
        "6a": ("copy_propagation", "Optimized IR (Copy Propagation)"),
        "6b": ("tuple_forwarding", "Optimized IR (Tuple Forwarding)"),
        "6c": ("alias_resolver", "Optimized IR (Alias Resolution)"),
        "6d": ("constant_folding", "Optimized IR (Constant Folding)"),
        "6e": ("dead_code_elimination", "Optimized IR (Dead Code Elimination)"),
        "6": ("optimized_ir", "Final Optimized IR"),
        "7": ("ir_partitioning", "Partitioned IR (Pre-trial/Per-trial)"),
        "8": ("recipe", "Final Simulation Recipe (Bytecode)"),
    }

    # Dynamically generate help text for the --compile argument
    stage_help_text = "Compile up to a specific stage and save the intermediate artifact. "
    for key, (name, desc) in STAGE_MAP.items():
        stage_help_text += f"'{key}' for {desc}. "
    stage_help_text += "Omitting this flag runs the full pipeline to generate the final .json recipe."

    parser = argparse.ArgumentParser(description="Compile a .vs file into a .json recipe.")
    parser.add_argument("input_file", nargs="?", default=None, help="The path to the input .vs file. Omit to read from stdin.")
    parser.add_argument("-o", "--output", dest="output_file", help="The path to the output .json file. Only used for full compilation.")
    parser.add_argument("-c", "--compile", type=str, choices=STAGE_MAP.keys(), help=stage_help_text)
    parser.add_argument("--lsp", action="store_true", help="Run the language server.")

    args = parser.parse_args()

    # --- LSP Handling ---
    if args.lsp:
        from vsc.server import start_server

        start_server()
        return

    # --- Input Validation ---
    if not args.input_file and sys.stdin.isatty():
        parser.error("input_file is required when not reading from a pipe.")

    script_path_for_display = args.input_file or "stdin"
    print(f"--- Compiling {script_path_for_display} ---")

    try:
        # --- Read Input ---
        if not args.input_file:
            script_content = sys.stdin.read()
            input_file_path_abs = None
        else:
            input_file_path_abs = os.path.abspath(args.input_file)
            with open(input_file_path_abs, "r", encoding="utf-8") as f:
                script_content = f.read()

        # --- Determine Pipeline Stop Point ---
        stop_after_stage = None
        if args.compile:
            stop_after_stage, stage_desc = STAGE_MAP[args.compile]

        # The compiler pipeline will automatically save the artifact if requested
        dump_stages = [stop_after_stage] if stop_after_stage else []

        # --- Run Compilation ---
        final_product = compile_valuascript(script_content, file_path=input_file_path_abs, dump_stages=dump_stages, stop_after_stage=stop_after_stage)

        # --- Handle Output ---
        if stop_after_stage:
            # The pipeline already prints the "Artifact saved" message.
            print(f"\n{TerminalColors.GREEN}--- Compilation to stage '{args.compile} ({stage_desc})' successful ---{TerminalColors.RESET}")
        else:
            # This block runs for a full compilation to the final recipe.
            if args.output_file:
                raw_output_path = args.output_file
            elif args.input_file:
                raw_output_path = os.path.splitext(args.input_file)[0] + ".json"
            else:
                raw_output_path = "stdin.json"

            output_file_path = os.path.abspath(raw_output_path)
            # Ensure the directory exists before writing
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(final_product, f, indent=2, cls=CompilerArtifactEncoder)

            print(f"\n{TerminalColors.GREEN}--- Compilation Successful ---{TerminalColors.RESET}")
            print(f"Recipe written to {output_file_path}")

    # --- Error Handling ---
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
        print(f"\n{TerminalColors.RED}--- UNEXPECTED COMPILER ERROR ---{TerminalColors.RESET}", file=sys.stderr)
        print(f"This may be a bug in the compiler. Please report it.", file=sys.stderr)
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        # --- Execution Time ---
        if "--lsp" not in sys.argv:
            end_time = time.perf_counter()
            duration = end_time - start_time
            print(f"\n{TerminalColors.CYAN}--- Total Execution Time: {duration:.4f} seconds ---{TerminalColors.RESET}")


if __name__ == "__main__":
    main()
