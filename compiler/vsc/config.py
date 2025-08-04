"""
Static configuration data for the ValuaScript compiler.
This includes directive rules, function signatures, and operator mappings.
"""

DIRECTIVE_CONFIG = {
    "iterations": {
        "required": True,
        "type": int,
        "error_missing": "The @iterations directive is mandatory (e.g., '@iterations = 10000').",
        "error_type": "The value for @iterations must be a whole number (e.g., 10000).",
    },
    "output": {
        "required": True,
        "type": str,
        "error_missing": "The @output directive is mandatory (e.g., '@output = final_result').",
        "error_type": "The value for @output must be a variable name (e.g., 'final_result').",
    },
    "output_file": {"required": False, "type": str, "error_type": 'The value for @output_file must be a string literal (e.g., "path/to/results.csv").'},
}

# Each function is now tagged with 'is_stochastic':
# - True: The function's output is random and must be re-evaluated for each trial.
#         This is the source of "impurity" that taints other dependent variables.
# - False: The function's output is deterministic given the same inputs.
#          It can be moved to the pre-trial phase if all its inputs are also deterministic.

FUNCTION_SIGNATURES = {
    # --- Mathematical & Logical Operations ---
    "add": {
        "variadic": True,
        "arg_types": [],
        "return_type": lambda types: "vector" if "vector" in types else "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise addition on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "subtract": {
        "variadic": True,
        "arg_types": [],
        "return_type": lambda types: "vector" if "vector" in types else "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise subtraction on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "multiply": {
        "variadic": True,
        "arg_types": [],
        "return_type": lambda types: "vector" if "vector" in types else "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise multiplication on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "divide": {
        "variadic": True,
        "arg_types": [],
        "return_type": lambda types: "vector" if "vector" in types else "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Performs element-wise division on two or more scalars or vectors.",
            "params": [{"name": "value1, value2, ...", "desc": "Two or more scalars or vectors."}],
            "returns": "A scalar or vector result.",
        },
    },
    "power": {
        "variadic": True,
        "arg_types": [],
        "return_type": lambda types: "vector" if "vector" in types else "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Raises the first argument to the power of the second.",
            "params": [{"name": "base", "desc": "The base value(s)."}, {"name": "exponent", "desc": "The exponent value(s)."}],
            "returns": "A scalar or vector result.",
        },
    },
    "identity": {
        "variadic": False,
        "arg_types": ["any"],
        "return_type": lambda types: types[0] if types else "any",
        "is_stochastic": False,
        "doc": {
            "summary": "Returns the input value unchanged. Useful for assigning a variable to another.",
            "params": [{"name": "value", "desc": "The value to return."}],
            "returns": "The original value.",
        },
    },
    "log": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the natural logarithm of a scalar.", "params": [{"name": "value", "desc": "The input scalar."}], "returns": "The natural logarithm as a scalar."},
    },
    "log10": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the base-10 logarithm of a scalar.", "params": [{"name": "value", "desc": "The input scalar."}], "returns": "The base-10 logarithm as a scalar."},
    },
    "exp": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the exponential (e^x) of a scalar.", "params": [{"name": "value", "desc": "The input scalar."}], "returns": "The exponential as a scalar."},
    },
    "sin": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the sine of a scalar.", "params": [{"name": "value", "desc": "The input scalar in radians."}], "returns": "The sine as a scalar."},
    },
    "cos": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the cosine of a scalar.", "params": [{"name": "value", "desc": "The input scalar in radians."}], "returns": "The cosine as a scalar."},
    },
    "tan": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the tangent of a scalar.", "params": [{"name": "value", "desc": "The input scalar in radians."}], "returns": "The tangent as a scalar."},
    },
    # --- Vector & Series Operations ---
    "compose_vector": {
        "variadic": True,
        "arg_types": ["scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Creates a new vector from a series of scalar values.",
            "params": [{"name": "value1, value2, ...", "desc": "The scalar values to include in the vector."}],
            "returns": "A new vector.",
        },
    },
    "sum_series": {
        "variadic": False,
        "arg_types": ["vector"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {"summary": "Calculates the sum of all elements in a vector.", "params": [{"name": "vector", "desc": "The input vector."}], "returns": "The sum as a scalar."},
    },
    "series_delta": {
        "variadic": False,
        "arg_types": ["vector"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the period-over-period change for a vector.",
            "params": [{"name": "vector", "desc": "The input vector."}],
            "returns": "A new vector of the differences, with one fewer element.",
        },
    },
    "npv": {
        "variadic": False,
        "arg_types": ["scalar", "vector"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the Net Present Value (NPV) of a series of cash flows.",
            "params": [{"name": "rate", "desc": "The discount rate per period."}, {"name": "cashflows", "desc": "A vector of cash flows."}],
            "returns": "The NPV as a scalar.",
        },
    },
    "compound_series": {
        "variadic": False,
        "arg_types": ["scalar", "vector"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Projects a base value forward using a vector of period-specific growth rates.",
            "params": [{"name": "base_value", "desc": "The starting scalar value."}, {"name": "rates_vector", "desc": "A vector of growth rates for each period."}],
            "returns": "A new vector of compounded values.",
        },
    },
    "get_element": {
        "variadic": False,
        "arg_types": ["vector", "scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Retrieves an element from a vector at a specific index.",
            "params": [{"name": "vector", "desc": "The source vector."}, {"name": "index", "desc": "The zero-based index of the element. Negative indices count from the end."}],
            "returns": "The element at the specified index as a scalar.",
        },
    },
    "delete_element": {
        "variadic": False,
        "arg_types": ["vector", "scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Returns a new vector with the element at the specified index removed.",
            "params": [{"name": "vector", "desc": "The source vector."}, {"name": "index", "desc": "The zero-based index of the element to remove. Negative indices count from the end."}],
            "returns": "A new vector with the element removed.",
        },
    },
    "grow_series": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Projects a series by applying a constant growth rate.",
            "params": [
                {"name": "base_value", "desc": "The starting scalar value."},
                {"name": "growth_rate", "desc": "The constant growth rate to apply each period (e.g., 0.05 for 5%)."},
                {"name": "periods", "desc": "The number of periods to project forward."},
            ],
            "returns": "A vector of projected values.",
        },
    },
    "interpolate_series": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Creates a vector by linearly interpolating between a start and end value.",
            "params": [
                {"name": "start_value", "desc": "The scalar value at the beginning of the series."},
                {"name": "end_value", "desc": "The scalar value at the end of the series."},
                {"name": "periods", "desc": "The total number of periods in the series."},
            ],
            "returns": "A new vector with the interpolated values.",
        },
    },
    "capitalize_expense": {
        "variadic": False,
        "arg_types": ["scalar", "vector", "scalar"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Calculates the value of capitalized assets (e.g., R&D) and the amortization for the current year.",
            "params": [
                {"name": "current_expense", "desc": "The expense in the current period."},
                {"name": "past_expenses", "desc": "A vector of expenses from prior periods, oldest first."},
                {"name": "amortization_period", "desc": "The number of years over which the expense is amortized."},
            ],
            "returns": "A two-element vector: [total_asset_value, amortization_for_current_year].",
        },
    },
    # --- Statistical Distributions (Samplers) ---
    "Normal": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Normal (Gaussian) distribution.",
            "params": [{"name": "mean", "desc": "The mean (μ) of the distribution."}, {"name": "std_dev", "desc": "The standard deviation (σ) of the distribution."}],
            "returns": "A random scalar sample.",
        },
    },
    "Lognormal": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Lognormal distribution.",
            "params": [
                {"name": "log_mean", "desc": "The mean of the underlying normal distribution."},
                {"name": "log_std_dev", "desc": "The standard deviation of the underlying normal distribution."},
            ],
            "returns": "A random scalar sample.",
        },
    },
    "Beta": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Beta distribution.",
            "params": [{"name": "alpha", "desc": "The alpha (α) shape parameter."}, {"name": "beta", "desc": "The beta (β) shape parameter."}],
            "returns": "A random scalar sample between 0 and 1.",
        },
    },
    "Uniform": {
        "variadic": False,
        "arg_types": ["scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Uniform distribution.",
            "params": [{"name": "min", "desc": "The minimum value of the range."}, {"name": "max", "desc": "The maximum value of the range."}],
            "returns": "A random scalar sample.",
        },
    },
    "Bernoulli": {
        "variadic": False,
        "arg_types": ["scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Bernoulli distribution (a single coin flip).",
            "params": [{"name": "p", "desc": "The probability of success (returning 1.0)."}],
            "returns": "Either 1.0 (success) or 0.0 (failure).",
        },
    },
    "Pert": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a PERT (a modified Beta) distribution.",
            "params": [
                {"name": "min", "desc": "The minimum possible value."},
                {"name": "most_likely", "desc": "The most likely value (the mode)."},
                {"name": "max", "desc": "The maximum possible value."},
            ],
            "returns": "A random scalar sample.",
        },
    },
    "Triangular": {
        "variadic": False,
        "arg_types": ["scalar", "scalar", "scalar"],
        "return_type": "scalar",
        "is_stochastic": True,
        "doc": {
            "summary": "Draws a random sample from a Triangular distribution.",
            "params": [
                {"name": "min", "desc": "The minimum possible value."},
                {"name": "most_likely", "desc": "The most likely value (the mode)."},
                {"name": "max", "desc": "The maximum possible value."},
            ],
            "returns": "A random scalar sample.",
        },
    },
    # --- Data Input (Always Pre-Trial) ---
    "read_csv_scalar": {
        "variadic": False,
        "arg_types": ["string", "string", "scalar"],
        "return_type": "scalar",
        "is_stochastic": False,
        "doc": {
            "summary": "Reads a single cell from a CSV file. Executed once before the simulation begins.",
            "params": [
                {"name": "file_path", "desc": "The path to the CSV file."},
                {"name": "column_name", "desc": "The name of the column to read from."},
                {"name": "row_index", "desc": "The zero-based index of the row to read."},
            ],
            "returns": "The value of the cell as a scalar.",
        },
    },
    "read_csv_vector": {
        "variadic": False,
        "arg_types": ["string", "string"],
        "return_type": "vector",
        "is_stochastic": False,
        "doc": {
            "summary": "Reads an entire column from a CSV file into a vector. Executed once before the simulation begins.",
            "params": [{"name": "file_path", "desc": "The path to the CSV file."}, {"name": "column_name", "desc": "The name of the column to read."}],
            "returns": "The column data as a new vector.",
        },
    },
}


OPERATOR_MAP = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide", "^": "power"}

TOKEN_FRIENDLY_NAMES = {
    "SIGNED_NUMBER": "a number",
    "CNAME": "a variable name",
    "expression": "a value or formula",
    "EQUAL": "an equals sign '='",
    "STRING": "a string in double quotes",
    "ADD": "a plus sign '+'",
    "SUB": "a minus sign '-'",
    "MUL": "a multiplication sign '*'",
    "DIV": "a division sign '/'",
    "POW": "a power sign '^'",
    "LPAR": "an opening parenthesis '('",
    "RPAR": "a closing parenthesis ')'",
    "LSQB": "an opening bracket '['",
    "RSQB": "a closing bracket ']'",
    "COMMA": "a comma ','",
    "AT": "an '@' symbol for a directive",
}
