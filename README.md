# ValuaScript & The Quantitative Simulation Engine

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-username/your-repo/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![C++ Version](https://img.shields.io/badge/C%2B%2B-17-blue.svg)](https://isocpp.org/std/the-standard)

**A high-performance, multithreaded C++ engine for quantitative financial modeling, driven by a simple, dedicated scripting language called ValuaScript.**

---

## 📖 About The Project

This project was born from the need to bridge the gap between the intuitive but slow nature of spreadsheet-based financial modeling and the powerful but often verbose nature of general-purpose programming languages. The goal is to provide a platform that offers the **usability** of a dedicated modeling language with the **raw performance** of compiled, multithreaded C++.

It is designed to execute complex, multi-year, stochastic financial models, running hundreds of thousands of Monte Carlo simulations in seconds—a task that would take minutes or hours in traditional tools.

### Key Features

- **✨ Simple & Intuitive Language:** Models are defined in **ValuaScript**, a clean, declarative language designed specifically for finance.
- **🚀 High-Performance Backend:** A core engine written in modern C++17, fully multithreaded to leverage all available CPU cores for maximum simulation speed.
- **🎲 Integrated Monte Carlo Simulation:** Natively supports a rich library of statistical distributions (`Normal`, `Pert`, `Lognormal`, etc.) for any input variable.
- **📈 Time-Series Aware:** Built from the ground up to handle multi-year forecasts, with operations for growth series, NPV, and element-wise vector math.
- **⚙️ Extensible & Modular:** The architecture, based on the Strategy pattern, is designed to be easily extended with new operations and distributions.
- **🛡️ Robust & Tested:** Comprehensive unit test suite built using GoogleTest, ensuring the correctness of all 33 features.

## 🏛️ Architecture

The platform is built on a clean, three-layer architecture that separates concerns for maximum flexibility and performance.

```
+------------------------+      +-------------------------+      +--------------------------+
|                        |      |                         |      |                          |
|   ValuaScript File     |----->|   Python Compiler       |----->|      JSON "Recipe"       |
|   (Human-Readable)     |      |   (Transpiles script)   |      |   (Intermediate Rep.)    |
|                        |      |                         |      |                          |
+------------------------+      +-------------------------+      +--------------------------+
                                                                             |
                                                                             |
                                             +-------------------------------+
                                             |
                                             v
                               +--------------------------+
                               |                          |
                               |  C++ Simulation Engine   |
                               |  (High-Performance)      |
                               |                          |
                               +--------------------------+
```

1.  **ValuaScript (The Frontend):** A user defines their model in a simple `.valuascript` file.
2.  **The Compiler (Python):** A Python script acts as a compiler, reading the `.valuascript` file and transpiling it into a structured JSON "recipe."
3.  **The C++ Engine (The Backend):** The multithreaded C++ executable (this repository) reads the JSON recipe and acts as a high-speed "interpreter" to run the simulation.

## 🛠️ Getting Started

Follow these steps to build and run the C++ engine on your local machine.

### Prerequisites

- A modern C++17 compliant compiler (e.g., GCC, Clang, MSVC)
- CMake (version 3.14 or higher)
- Git

### Build Instructions

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/your-repo.git
    cd your-repo
    ```

2.  **Configure with CMake:**
    The project uses `FetchContent` to automatically download and manage dependencies, so no manual installation of libraries is needed.

    ```bash
    # Create a build directory
    cmake -B build
    ```

3.  **Compile the project:**
    ```bash
    # From the root directory, build all targets
    cmake --build build
    ```
    This will create two executables in the `build/bin` directory: `monte-carlo-simulator` and `run_tests`.

## 🚀 Usage

The C++ engine is a command-line application that takes the path to a JSON recipe file as its only argument.

```bash
# Run a simulation using a specific recipe
./build/bin/monte-carlo-simulator /path/to/your/recipe.json
```

The engine will execute the simulation and print a statistical summary of the results to the terminal.

### 📜 ValuaScript Language Guide (The Vision)

_This section describes the target language, **ValuaScript**, which will be built in the next phase._

**Settings:** Configure the simulation using special comments.

```swift
#iterations = 100000
#output = final_share_price
```

**Variable Assignment:** Use the `let` keyword. The type is inferred.```swift

# Fixed Scalar

let tax_rate = 0.21

# Fixed Vector (Time-Series)

let margin_forecast = [0.25, 0.26, 0.27, 0.28, 0.29]

# Stochastic Variable (Distribution)

let growth_rate = Normal(0.08, 0.02)
let wacc = Pert(0.08, 0.09, 0.10)

# Operations: Use functions for calculations. Expressions can be nested.

```swift
# Simple arithmetic
let total_capital = add(market_cap_equity, debt)

# Nested expression
let nopat = multiply(EBIT, subtract(1, tax_rate))

# Time-series functions
let revenue_series = grow_series(base_revenue, growth_rate, 10)
let total_npv = npv(wacc, revenue_series)
```

## 🔬 Development & Contribution

Contributions are welcome! The project is designed to be highly extensible.

### Running Tests

The project includes a comprehensive unit test suite using GoogleTest. To run the tests, build the project and then execute the `run_tests` binary.

```bash
./build/bin/run_tests
```

### Adding a New Distribution

Follow these steps to add a new probability distribution to the engine:

1.  **Define the Class:** Create `NewDistribution.h` in `include/distributions/` and `NewDistribution.cpp` in `src/distributions/`. Ensure the class inherits from `IDistribution` and implements the `double getSample()` method.
2.  **Update `datastructures.h`:** Add your new distribution to the `DistributionType` enum in `include/engine/datastructures.h`.
    ```cpp
    enum class DistributionType { ..., Beta, NewDistribution };
    ```
3.  **Update `SimulationEngine.cpp` (Map):** Add the JSON string-to-enum mapping in the `STRING_TO_DIST_TYPE_MAP` at the top of `src/engine/SimulationEngine.cpp`.
    ```cpp
    { "New", DistributionType::NewDistribution }
    ```
4.  **Update `SimulationEngine.cpp` (Factory):** Add a `case` to the `switch` statement within the `create_distribution_from_input` method to construct your new class.
5.  **Add a Unit Test:** In `test/distributions_tests.cpp`, add a new `TEST` to verify the statistical properties (e.g., mean, bounds) of your new distribution.

### Adding a New Operation

Follow these steps to add a new operation:

1.  **Update `datastructures.h`:** Add your new operation to the `OpCode` enum in `include/engine/datastructures.h`.
    ```cpp
    enum class OpCode { ..., CAPITALIZE_EXPENSE, NEW_OPERATION };
    ```
2.  **Update `SimulationEngine.cpp` (Map):** Add the JSON string-to-enum mapping in the `STRING_TO_OPCODE_MAP` at the top of `src/engine/SimulationEngine.cpp`.
    ```cpp
    { "new_operation", OpCode::NEW_OPERATION }
    ```
3.  **Define the Class:** In `include/engine/operations.h`, create a new class `NewOperation` that inherits from `IOperation` and implements the `TrialValue execute(...)` method.
4.  **Update `SimulationEngine.cpp` (Factory):** Add your new operation to the factory map in the `build_operation_factory` method.
    ```cpp
    ops[OpCode::NEW_OPERATION] = std::make_unique<NewOperation>();
    ```
5.  **Update `SimulationEngine.cpp` (Compiler Check):** Add a `case` for your new `OpCode` to the `switch` statement at the end of `build_operation_factory`. This provides a compile-time check to ensure all opcodes are handled.
6.  **Add a Unit Test:** In `test/engine_tests.cpp`, add a new parameterized test case to the appropriate `INSTANTIATE_TEST_SUITE_P` block to verify your operation's logic.

## 🗺️ Roadmap

- [x] **V1.0 C++ Engine Core**
  - [x] Generic, data-driven architecture
  - [x] Full library of statistical distributions
  - [x] Time-series and vector math support
  - [x] Recursive expression evaluation
  - [x] Multithreaded execution
  - [x] Comprehensive unit test suite
- [ ] **V1.1 ValuaScript Compiler**
  - [ ] Define final ValuaScript grammar using Lark
  - [ ] Implement Python-based transpiler to JSON
  - [ ] Create command-line interface for the compiler

## 📄 License

This project is distributed under the MIT License. See the `LICENSE` file for more information.
