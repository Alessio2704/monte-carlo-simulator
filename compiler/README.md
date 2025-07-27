# ValuaScript Compiler (vsc)

This directory contains the Python-based compiler for the ValuaScript language. It transpiles `.vs` files into a JSON recipe that can be consumed by the C++ simulation engine.

## Installation

This tool can be installed as a command-line utility. From within this directory, it is recommended to use a virtual environment.

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install the compiler and its dependencies
pip install .
```

## Usage

Once installed, the `vsc` command will be available in your shell.

```bash
# Compile a script (output will be my_model.json)
vsc /path/to/my_model.vs

# Specify an output file
vsc /path/to/my_model.vs -o /path/to/recipe.json
```
