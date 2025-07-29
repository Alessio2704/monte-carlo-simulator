# ValuaScript & The Quantitative Simulation Engine

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/Alessio2704/monte-carlo-simulator/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![C++ Version](https://img.shields.io/badge/C%2B%2B-17-blue.svg)](https://isocpp.org/std/the-standard)
[![Python Version](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)

**A high-performance, multithreaded C++ engine for quantitative financial modeling, driven by ValuaScript—a simple, dedicated scripting language with a smart, validating compiler.**

## 📖 About The Project

This project was born from the need to bridge the gap between the intuitive but slow nature of spreadsheet-based financial modeling and the powerful but often verbose nature of general-purpose programming languages. The goal is to provide a platform that offers the **usability** of a dedicated modeling language with the **raw performance** of compiled, multithreaded C++.

It is designed to execute complex, multi-year, stochastic financial models, running hundreds of thousands of Monte Carlo simulations in seconds—a task that would take minutes or hours in traditional tools.

### Key Features

- **✨ Simple & Intuitive Language:** Models are defined in **ValuaScript (`.vs`)**, a clean, declarative language with a **familiar, spreadsheet-like formula syntax** using standard mathematical operators (`+`, `-`, `*`, `/`, `^`).
- **🚀 High-Performance Backend:** A core engine written in modern C++17, fully multithreaded to leverage all available CPU cores for maximum simulation speed.
- **🐍 Smart Validating Compiler:** A robust compiler, `vsc`, transpiles ValuaScript into a JSON recipe. It provides **clear, user-friendly error messages** and performs advanced **static type inference** to catch logical errors before execution.
- **⚙️ Streamlined Workflow:** A `--run` flag allows for a seamless, one-step compile-and-execute experience.
- **📊 Instant Visualization:** A `--plot` flag automatically generates a histogram of the simulation output, providing immediate visual analysis.
- **📈 Data Export:** Natively supports exporting full simulation trial data to CSV files for further analysis with the `@output_file` directive.
- **🎲 Integrated Monte Carlo Simulation:** Natively supports a rich library of statistical distributions (`Normal`, `Pert`, `Lognormal`, etc.) with fully validated parameters.
- **🛡️ Robust & Tested:** Comprehensive unit test suite for both the C++ engine (GoogleTest) and the Python compiler (Pytest), ensuring correctness and stability.

## 🏛️ Architecture

The platform is built on a clean, three-layer architecture that separates human-readable modeling from high-speed computation.

```mermaid
graph TD;
    A["<b>ValuaScript File (.vs)</b><br/><i>Human-Readable Model</i>"] -- "vsc my_model.vs --run" --> B["<b>vsc Compiler (Python)</b><br/><i>Validates, translates, & executes</i>"];
    B -- generates & consumes --> C["<b>JSON Recipe</b><br/><i>Intermediate Representation</i>"];
    C -- consumed by --> D["<b>Simulation Engine (C++)</b><br/><i>High-Performance Backend</i>"];
    D -- produces --> E["<b>Simulation Results</b><br/><i>Statistical Analysis & Plot</i>"];

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#ccf,stroke:#333,stroke-width:2px
    style D fill:#9f9,stroke:#333,stroke-width:2px
```

## 🚀 Getting Started

There are two paths for using this project: as an **End-User** (recommended for most) or as a **Developer** (if you want to contribute).

### For End-Users

1.  **Download the `vsc` Compiler:**
    Go to the [**latest GitHub Release**](https://github.com/Alessio2704/monte-carlo-simulator/releases) and download the `vsc` executable for your operating system. Place it in a convenient location.

2.  **Build the C++ Engine:**
    You only need to do this once. First, ensure you have [Git](https://git-scm.com/), [CMake](https://cmake.org/), and a C++17 compiler installed.

    ```bash
    # Clone the repository
    git clone https://github.com/Alessio2704/monte-carlo-simulator.git
    cd monte-carlo-simulator

    # Configure and build the C++ engine
    cmake -B build
    cmake --build build
    ```

    This creates the `monte-carlo-simulator` executable inside the `build/bin/` directory.

3.  **Configure the `--run` Flag (One-Time Setup):**
    To use the streamlined workflow, you need to tell the `vsc` compiler where to find the C++ engine you just built. Follow the platform-specific instructions in the **"Configuring the `--run` Flag"** section below.

### Full Workflow Example

Once set up, you can compile, run, and visualize a simulation with a single command:

1.  **Write a model** in a file named `my_model.vs`. Make sure it includes an `@output_file` directive.
2.  **Compile, run, and plot it:**
    ```bash
    # This will compile my_model.vs to my_model.json,
    # execute the simulation, save results to the specified CSV,
    # and finally display a histogram of the results.
    /path/to/downloaded/vsc my_model.vs --run --plot
    ```

---

## ⚙️ Configuring the `--run` Flag

To make `vsc my_model.vs --run` work seamlessly, you need to tell the `vsc` compiler where to find the `monte-carlo-simulator` executable. The recommended method is to set an environment variable. This is a one-time setup.

First, get the **absolute path** to your C++ engine executable. You can find this by navigating to its directory and running `pwd` (on macOS/Linux) or copying the path from File Explorer (on Windows).

- Example path on macOS/Linux: `/Users/yourname/monte-carlo-simulator/build/bin/monte-carlo-simulator`
- Example path on Windows: `C:\Users\yourname\monte-carlo-simulator\build\bin\monte-carlo-simulator.exe`

<details>
<summary><b>Click for macOS & Linux Instructions (Zsh/Bash)</b></summary>

1.  **Open your shell configuration file.** This is typically `~/.zshrc` for Zsh (default on modern macOS) or `~/.bash_profile` or `~/.bashrc` for Bash.
    ```bash
    # For Zsh
    open ~/.zshrc
    ```
2.  **Add the `export` command.** Go to the very bottom of the file and add the following line, replacing the example path with your own.

    ```bash
    # Set the path for the ValuaScript Simulation Engine
    export VSC_ENGINE_PATH="/Users/yourname/monte-carlo-simulator/build/bin/monte-carlo-simulator"
    ```

3.  **Save the file and apply the changes** by running `source ~/.zshrc` or by opening a new terminal window.

</details>

<details>
<summary><b>Click for Windows Instructions</b></summary>

1.  **Open Environment Variables:** Open the Start Menu, type "env", and select "Edit the system environment variables".
2.  **Edit User Variables:** In the window that appears, click the "Environment Variables..." button. In the top section ("User variables for yourname"), click "New...".
3.  **Create the Variable:**
    - **Variable name:** `VSC_ENGINE_PATH`
    - **Variable value:** `C:\Users\yourname\monte-carlo-simulator\build\bin\monte-carlo-simulator.exe` (replace with your actual path)
4.  **Confirm:** Click OK on all the windows to close them. You must **open a new Command Prompt or PowerShell terminal** for the changes to take effect.

</details>

<details>
<summary><b>Alternative Methods (for advanced users)</b></summary>

The `vsc` compiler searches for the engine in this order:

1.  A path specified with the `--engine-path` flag (e.g., `vsc model.vs --run --engine-path /path/to/engine`).
2.  The `VSC_ENGINE_PATH` environment variable (recommended setup).
3.  A known relative path (`../../build/bin/monte-carlo-simulator`), which works out-of-the-box for developers running `vsc` from within the Python package source.
4.  The system's `PATH` variable.

</details>

---

### For Developers (Building Everything from Source)

<details>
<summary>Click to expand developer instructions</summary>

Follow the "Getting Started" instructions to clone and build the C++ engine. Then, set up the Python environment:

```bash
cd compiler
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate
# Install the vsc package in editable mode and its dependencies
pip install -e .
```

To run the test suite, you will need to install `pytest`:
```bash
pip install pytest
```

The `vsc` command is now available in your shell. The `--run` flag will work automatically for developers without any configuration, as it will find the engine at the known relative path.

</details>

## 📜 ValuaScript Language Guide

ValuaScript uses a simple, line-by-line syntax for defining variables and calculations. The compiler enforces a clean, readable style.

#### Settings

Special `@` directives configure the simulation. They can appear anywhere in the file but are typically placed at the top for clarity.

```valuascript
# Defines the number of Monte Carlo trials to run. (Required)
@iterations = 100000

# Specifies which variable's final value should be collected. (Required)
@output = final_share_price

# Exports all trial results to a CSV for analysis and plotting. (Optional)
@output_file = "sim_results/amazon_model.csv"
```

#### Variable Assignment (`let`)

Use the `let` keyword to define variables. The compiler executes assignments sequentially and infers the type of each variable (`scalar` or `vector`).

**1. Literals (Scalars and Vectors)**

```valuascript
let tax_rate = 0.21              # Inferred as 'scalar'
let margin_forecast = [0.25, 0.26] # Inferred as 'vector'
```

**2. Infix Expressions**
ValuaScript supports standard mathematical operators for calculations, with correct precedence (`^` before `*`/`/`, before `+`/`-`). Parentheses `()` can be used to control the order of evaluation.

```valuascript
# The compiler infers the types of the variables and the final result.
let cost_of_equity = risk_free_rate + beta * equity_risk_premium
```

**3. Function Calls**
For more complex logic, the engine provides a rich library of built-in functions. The compiler performs advanced, recursive type checking on all function calls:

- The number of arguments must be correct.
- The type of each argument (`scalar` or `vector`) must match the function's signature. This includes the results of nested function calls.

```valuascript
# CORRECT: The result of grow_series (a vector) is a valid argument for sum_series.
let total_sales = sum_series(grow_series(100, 0.1, 5))

# INCORRECT: The result of grow_series (a vector) is not a valid argument
# for the 'mean' parameter of Normal, which expects a scalar.
# THIS WILL CAUSE A COMPILER ERROR:
# let random_value = Normal(grow_series(100, 0.1, 5), 10)
```

## 🔬 Development & Contribution

Contributions are welcome! The project is designed to be highly extensible. The compiler code is now a proper Python package located in the `compiler/vsc/` directory.

### Running Tests

The project includes comprehensive test suites for both the C++ engine and the Python compiler.

**1. C++ Engine Tests (GoogleTest)**

```bash
# First, build the project (see instructions above)
./build/bin/run_tests
```

**2. Python Compiler Tests (Pytest)**

```bash
cd compiler
source venv/bin/activate
pytest -v
```

### Extending the Engine: A Detailed Guide

Adding a new function is a three-step process that touches both the C++ engine and the Python compiler package. A full example is available in the project's development history. The key steps are:
1.  **C++ Engine:** Create a new class inheriting from `IExecutable` in `include/engine/` and register it in the factory in `src/engine/SimulationEngine.cpp`.
2.  **Python Compiler:** Add the function's signature to `FUNCTION_SIGNATURES` in `compiler/vsc/config.py`.
3.  **Testing:** Add comprehensive unit tests to `test/engine_tests.cpp` (for logic) and `compiler/tests/test_compiler.py` (for validation).


## 🗺️ Roadmap

The project is actively developed. Our current roadmap prioritizes practical utility and user experience.

### ✅ Completed Milestones
- **V1.0:** Core C++ Engine & ValuaScript Compiler.
- **V1.1:** Compiler with full type inference & robust error reporting.
- **V1.2:**
  - Streamlined `--run` flag.
  - Data export via `@output_file` and CSV writing.
  - Instant visualization via `--plot` flag.
  - Compiler refactored into a scalable Python package.

---

### 🔜 Tier 1: Next Immediate Feature

- [ ] **External Data Integration (`read_csv`)**
  - **Why:** To enable models to use real-world data (e.g., historical financials, assumption sets) from external files, which is a critical feature for any serious modeling tool.
  - **How:**
    1.  **Engine:** Add a C++ CSV parsing library. Implement a new `ReadCsvOperation` that takes a file path and column name, reads the data, and returns a vector.
    2.  **Compiler:** Add a `read_csv(string, string) -> vector` function signature. The compiler will validate the call and pass the arguments to the JSON recipe.

---

### ⏩ Tier 2: Improving the User Experience

- [ ] **VS Code Extension**
  - **Why:** To transform the model-writing process from editing plain text to working in a smart environment. This dramatically lowers the barrier to entry and improves productivity.
  - **How:**
    1.  **Phase 1 (Easy):** Implement syntax highlighting for `.vs` files and snippets for common functions.
    2.  **Phase 2 (Advanced):** Develop a Language Server that uses the `vsc` compiler package to provide real-time error checking (linting) and diagnostics directly in the editor.

---

### 🚀 Tier 3: Advanced Language Features

- [ ] **Modularization (`@import` / `@export`)**
  - **Why:** To allow users to create reusable, importable modules (e.g., a standard WACC calculation). This promotes cleaner, more abstract, and more scalable models, avoiding code duplication.
  - **How:** This is a major architectural evolution for the compiler. It will require implementing a dependency graph, handling namespaces (to prevent variable collisions), and defining a clear contract for how modules pass arguments and return values.

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more information.