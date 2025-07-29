"""
Utility functions for the ValuaScript compiler, including terminal coloring,
error formatting, executable searching, and output plotting.
"""

import os
from shutil import which
from lark.exceptions import UnexpectedInput, UnexpectedCharacters
from .config import TOKEN_FRIENDLY_NAMES


class TerminalColors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"


def format_lark_error(e, script_content: str) -> str:
    if isinstance(e, UnexpectedCharacters):
        line, column, custom_msg = e.line, e.column, "Invalid character or syntax."
    elif isinstance(e, UnexpectedInput):
        line, column = e.line, e.column
        line_content = script_content.splitlines()[line - 1].strip()
        if "(" in line_content and ")" not in line_content:
            custom_msg = "It looks like you have an opening parenthesis '(' without a matching closing one ')'."
        elif "[" in line_content and "]" not in line_content:
            custom_msg = "It looks like you have an opening bracket '[' without a matching closing one ']'."
        else:
            expected_str = ", ".join(sorted([TOKEN_FRIENDLY_NAMES.get(s, s) for s in e.expected]))
            custom_msg = f"The syntax is invalid here. I was expecting {expected_str}."
    else:
        return f"\n{TerminalColors.RED}--- PARSING ERROR ---\n{e}{TerminalColors.RESET}"
    error_header = f"\n{TerminalColors.RED}--- SYNTAX ERROR ---{TerminalColors.RESET}"
    line_indicator = f"L{line} | {script_content.splitlines()[line - 1]}"
    pointer = f"{' ' * (column + 2 + len(str(line)))}^\n"
    error_message = f"{TerminalColors.RED}Error at line {line}: {custom_msg}{TerminalColors.RESET}"
    return f"{error_header}\n{line_indicator}\n{pointer}{error_message}"


def find_engine_executable(provided_path):
    if provided_path and os.path.isfile(provided_path) and os.access(provided_path, os.X_OK):
        return provided_path
    env_path = os.environ.get("VSC_ENGINE_PATH")
    if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
        return env_path
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        dev_path = os.path.join(script_dir, "..", "..", "build", "bin", "monte-carlo-simulator")
        if os.path.isfile(dev_path) and os.access(dev_path, os.X_OK):
            return dev_path
    except NameError:
        pass
    if which("monte-carlo-simulator"):
        return which("monte-carlo-simulator")
    return None


def generate_and_show_plot(file_path: str):
    """Reads a CSV output file and displays a histogram of the results."""
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"{TerminalColors.RED}Error: Plotting requires 'pandas' and 'matplotlib'.\nPlease install them with 'pip install pandas matplotlib'.{TerminalColors.RESET}")
        return

    df = pd.read_csv(file_path)

    if df.empty:
        print("Output file is empty. Nothing to plot.")
        return

    if "Result" in df.columns:
        target_column = "Result"
    elif "Period_1" in df.columns:
        target_column = "Period_1"
        print(f"{TerminalColors.YELLOW}Note: Plotting distribution for 'Period_1'. Vector output detected.{TerminalColors.RESET}")
    else:
        target_column = df.columns[0]
        print(f"{TerminalColors.YELLOW}Warning: Plotting distribution for the first column '{target_column}'.{TerminalColors.RESET}")

    data = df[target_column]
    mean, std = data.mean(), data.std()

    plt.figure(figsize=(10, 6))
    plt.hist(data, bins=50, density=True, alpha=0.7, label="Distribution")
    plt.title(f'Simulation Output Distribution for "{target_column}"')
    plt.xlabel("Value")
    plt.ylabel("Probability Density")
    plt.axvline(mean, color="r", linestyle="dashed", linewidth=2, label=f"Mean: {mean:.2f}")
    stats_text = f"Std. Dev: {std:.2f}\nTrials: {len(data)}"
    plt.text(0.05, 0.95, stats_text, transform=plt.gca().transAxes, fontsize=10, verticalalignment="top", bbox=dict(boxstyle="round,pad=0.5", fc="wheat", alpha=0.5))
    plt.legend()
    plt.grid(True, alpha=0.3)

    print("Displaying plot. Close the plot window to exit.")
    plt.show()
