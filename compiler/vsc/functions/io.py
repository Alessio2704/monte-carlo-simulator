"""
Signatures for data input/output functions.
"""

SIGNATURES = {
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
