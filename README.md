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
- **🎲 Integrated Monte Carlo Simulation:** Natively supports a rich library of statistical distributions (`Normal`, `Pert`, `Lognormal`, etc.) with fully validated parameters.
- **📈 Time-Series Aware:** Built from the ground up to handle multi-year forecasts, with operations for growth series, NPV, and element-wise vector math.
- **🛡️ Robust & Tested:** Comprehensive unit test suite for both the C++ engine (GoogleTest) and the Python compiler (Pytest), ensuring correctness and stability.

## 🏛️ Architecture

The platform is built on a clean, three-layer architecture that separates human-readable modeling from high-speed computation.

```mermaid
graph TD;
    A["<b>ValuaScript File (.vs)</b><br/><i>Human-Readable Model</i>"] -- transpiles via --> B["<b>vsc Compiler (Python)</b><br/><i>Validates types & translates</i>"];
    B -- generates --> C["<b>JSON Recipe</b><br/><i>Intermediate Representation</i>"];
    C -- consumed by --> D["<b>Simulation Engine (C++)</b><br/><i>High-Performance Backend</i>"];
    D -- produces --> E["<b>Simulation Results</b><br/><i>Statistical Analysis</i>"];

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#ccf,stroke:#333,stroke-width:2px
    style D fill:#9f9,stroke:#333,stroke-width:2px
```

1.  **ValuaScript (Frontend):** A user defines their model in a simple `.vs` file.
2.  **`vsc` Compiler (Middleware):** The Python-based `vsc` tool reads the `.vs` file, validates its syntax, logic, and types, and transpiles it into a structured JSON "recipe."
3.  **Simulation Engine (Backend):** The multithreaded C++ `monte-carlo-simulator` executable reads the JSON recipe and acts as a high-speed, sequential interpreter to run the simulation.

## 🚀 Getting Started

There are two paths for using this project: as an **End-User** (recommended for most) or as a **Developer** (if you want to contribute).

### For End-Users (The Easy Way)

This path allows you to write models and run simulations without setting up a Python environment.

1.  **Download the `vsc` Compiler:**
    Go to the [**latest GitHub Release**](https://github.com/Alessio2704/monte-carlo-simulator/releases) and download the `vsc` executable for your operating system.

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

### Full Workflow Example

With the setup complete, you can now write, compile, and run models.

1.  **Write a model** in a file named `my_model.vs`.
2.  **Compile it** using the `vsc` executable you downloaded:
    ```bash
    # This creates my_model.json
    /path/to/downloaded/vsc my_model.vs
    ```
3.  **Run the simulation** with the C++ engine:
    ```bash
    ./build/bin/monte-carlo-simulator my_model.json
    ```

---

### For Developers (Building Everything from Source)

<details>
<summary>Click to expand developer instructions</summary>

This path is for those who wish to modify the compiler or the C++ engine.

#### 📋 Prerequisites

- **Git:** To clone the repository.
- **C++ Compiler (C++17):** e.g., Clang, GCC, or MSVC.
- **CMake (3.14+):** To build the C++ engine.
- **Python (3.7+):** To build and run the `vsc` compiler from source.

#### 🛠️ Build Instructions

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Alessio2704/monte-carlo-simulator.git
    cd monte-carlo-simulator
    ```
2.  **Build the C++ Engine:**
    ```bash
    cmake -B build
    cmake --build build
    ```
3.  **Build and Install the `vsc` Compiler:**
    ```bash
    cd compiler
    # Create a virtual environment
    python3 -m venv venv
    source venv/bin/activate
    # Install in editable mode and install test dependencies
    pip install -e .
    pip install pytest
    ```
    The `vsc` command is now available in your shell as long as the virtual environment is active.

</details>

## 📜 ValuaScript Language Guide

ValuaScript uses a simple, line-by-line syntax for defining variables and calculations. The compiler enforces a clean, readable style.

#### Settings

Special `@` directives configure the simulation. They can appear anywhere in the file but are required.

```valuascript
# Defines the number of Monte Carlo trials to run.
@iterations = 100000

# Specifies which variable's final value should be collected.
@output = final_share_price
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

Contributions are welcome! The project is designed to be highly extensible.

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

Adding a new function is a three-step process that touches both the C++ engine and the Python compiler.

---

#### Example 1: Adding a New Operation (`stdev`)

Let's add a `stdev` function that calculates the standard deviation of a vector.

**Step 1: Implement the Logic in C++**

1.  **Create the Class:** In `include/engine/operations.h`, create a new class that inherits from `IExecutable`.

    ```cpp
    // In include/engine/operations.h
    class StdevOperation : public IExecutable {
    public:
        TrialValue execute(const std::vector<TrialValue>& args) const override {
            const auto& series = std::get<std::vector<double>>(args[0]);
            if (series.empty()) return 0.0;
            double sum = std::accumulate(series.begin(), series.end(), 0.0);
            double mean = sum / series.size();
            double sq_sum = std::inner_product(series.begin(), series.end(), series.begin(), 0.0);
            double stdev = std::sqrt(sq_sum / series.size() - mean * mean);
            return stdev;
        }
    };
    ```

2.  **Register in Factory:** In `src/engine/SimulationEngine.cpp`, add it to the `build_executable_factory` method.

    ```cpp
    // In src/engine/SimulationEngine.cpp
    m_executable_factory["stdev"] = [] { return std::make_unique<StdevOperation>(); };
    ```

**Step 2: Update the Python Compiler**

1.  **Add to Signatures:** In `compiler/vsc.py`, add an entry to the `FUNCTION_SIGNATURES` dictionary.

    ```python
    # In compiler/vsc.py
    "stdev": {"variadic": False, "arg_types": ["vector"], "return_type": "scalar"},
    ```

**Step 3: Add Tests (Crucial!)**

1.  **C++ Test:** In `test/engine_tests.cpp`, add a test case to validate the logic.
2.  **Python Tests:** In `compiler/tests/test_compiler.py`, add tests for the compiler's validation (e.g., test that `stdev(123)` fails and `stdev([1,2])` passes).

---

#### Example 2: Adding a New Distribution (`Poisson`)

Let's add a `Poisson` distribution sampler.

**Step 1: Implement the Logic in C++**

1.  **Create the Class:** In `include/engine/samplers.h`, create the new sampler class.

    ```cpp
    // In include/engine/samplers.h
    class PoissonSampler : public IExecutable {
    public:
        TrialValue execute(const std::vector<TrialValue>& args) const override {
            // The compiler guarantees we get one scalar argument.
            double lambda = std::get<double>(args[0]);
            std::poisson_distribution<> dist(lambda);
            return static_cast<double>(dist(get_thread_local_generator()));
        }
    };
    ```

2.  **Register in Factory:** In `src/engine/SimulationEngine.cpp`, add it to the factory.

    ```cpp
    // In src/engine/SimulationEngine.cpp
    m_executable_factory["Poisson"] = [] { return std::make_unique<PoissonSampler>(); };
    ```

**Step 2: Update the Python Compiler**

1.  **Add to Signatures:** In `compiler/vsc.py`, add the new function's signature.

    ```python
    # In compiler/vsc.py
    "Poisson": {"variadic": False, "arg_types": ["scalar"], "return_type": "scalar"},
    ```

**Step 3: Add Tests (Crucial!)**

1.  **C++ Test:** In `test/engine_tests.cpp`, add a statistical test to verify the mean of many samples.
2.  **Python Tests:** In `compiler/tests/test_compiler.py`, add arity and type tests (e.g., `Poisson()` and `Poisson([1,2])` should fail).

By following these three steps, your new function will be fully and safely integrated into the entire platform.

## 🗺️ Roadmap

- [x] **V1.0 C++ Engine Core & ValuaScript Compiler**
- [x] **V1.1 Compiler Upgrade with Full Type Inference & Robust Error Reporting**

---

### Tier 1: Major Features (V1.2+)

<details>
<summary>These features will significantly expand the capabilities of the platform.</summary>

- [ ] **External Data Integration:**
  - [ ] Add a `read_csv("path", "column")` function to ValuaScript to allow models to use external data sources.
- [ ] **Streamlined Workflow:**
  - [ ] Add a `--run` flag to the `vsc` compiler to automatically execute the simulation after compilation.
- [ ] **Enhanced Output Options:**
  - [ ] Add an `@output_file = "results.csv"` directive to write all trial results to a file.

</details>

### Tier 2: Ecosystem and Distribution (V2.0)

<details>
<summary>Long-term goals focused on making the project more accessible and professional.</summary>

- [ ] **Automated Cross-Platform Builds (CI/CD):**
  - [ ] Create a GitHub Actions workflow to automatically build binaries for all major OSes and attach them to new GitHub Releases.
- [ ] **Dedicated Documentation Website:**
  - [ ] Use a static site generator like MkDocs or Docusaurus for full, searchable documentation.

</details>

### The "Blue Sky" Vision

<details>
<summary>Ambitious, long-term ideas for a next-generation modeling tool.</summary>

- [ ] **VS Code Extension:**
  - [ ] Develop an extension for Visual Studio Code providing syntax highlighting, real-time error checking (linting), and autocompletion.
- [ ] **Data Visualization:**
  - [ ] Add a feature to automatically generate and display a histogram of the final output distribution.

</details>

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more information.
