#include "include/engine/functions/operations.h"
#include <stdexcept>
#include <cmath>
#include <numeric>
#include <variant>
#include <vector>
#include <memory>
#include "csv.hpp"

// Helper to perform a variadic operation on a list of scalars
inline double perform_variadic_op(OpCode code, const std::vector<double> &values)
{
    if (values.empty())
    {
        throw std::runtime_error("Cannot perform operation on an empty list of values.");
    }

    double accumulator = values[0];
    for (size_t i = 1; i < values.size(); ++i)
    {
        switch (code)
        {
        case OpCode::ADD:
            accumulator += values[i];
            break;
        case OpCode::SUBTRACT:
            accumulator -= values[i];
            break;
        case OpCode::MULTIPLY:
            accumulator *= values[i];
            break;
        case OpCode::DIVIDE:
            if (values[i] == 0.0)
                throw std::runtime_error("Division by zero");
            accumulator /= values[i];
            break;
        case OpCode::POWER:
            accumulator = std::pow(accumulator, values[i]);
            break;
        default:
            throw std::logic_error("Unsupported variadic op code.");
        }
    }
    return accumulator;
}

// This is a binary visitor for std::visit.
struct ElementWiseVisitor
{
    OpCode code;

    // --- Valid Numeric Operations ---

    TrialValue operator()(double left, double right) const
    {
        return perform_variadic_op(code, {left, right});
    }

    // Case: vector op scalar
    TrialValue operator()(const std::vector<double> &vec, double scalar) const
    {
        std::vector<double> result;
        result.reserve(vec.size());
        for (double val : vec)
        {
            result.push_back(perform_variadic_op(code, {val, scalar}));
        }
        return result;
    }

    // Case: scalar op vector
    TrialValue operator()(double scalar, const std::vector<double> &vec) const
    {
        std::vector<double> result;
        result.reserve(vec.size());
        for (double val : vec)
        {
            result.push_back(perform_variadic_op(code, {scalar, val}));
        }
        return result;
    }

    // Case: vector op vector
    TrialValue operator()(const std::vector<double> &vec_left, const std::vector<double> &vec_right) const
    {
        if (vec_left.size() != vec_right.size())
            throw std::runtime_error("Vector size mismatch for element-wise operation.");
        std::vector<double> result;
        result.reserve(vec_left.size());
        for (size_t i = 0; i < vec_left.size(); ++i)
        {
            result.push_back(perform_variadic_op(code, {vec_left[i], vec_right[i]}));
        }
        return result;
    }

    // --- Invalid Operations Involving Strings ---
    template <typename T>
    TrialValue operator()(const std::string &, T) const
    {
        throw std::logic_error("Mathematical operations on strings are not supported.");
    }
    template <typename T>
    TrialValue operator()(T, const std::string &) const
    {
        throw std::logic_error("Mathematical operations on strings are not supported.");
    }
    TrialValue operator()(const std::string &, const std::string &) const
    {
        throw std::logic_error("Mathematical operations on strings are not supported.");
    }
};
// --- IExecutable Implementations ---

VariadicBaseOperation::VariadicBaseOperation(OpCode code) : m_code(code) {}

TrialValue VariadicBaseOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.empty())
        throw std::runtime_error("Operation requires at least one argument.");
    if (args.size() == 1)
        return args[0];

    // First, check for the simple all-scalar case for efficiency
    bool has_vector = false;
    for (const auto &arg : args)
    {
        if (std::holds_alternative<std::vector<double>>(arg))
        {
            has_vector = true;
            break;
        }
    }

    if (!has_vector)
    {
        std::vector<double> values;
        values.reserve(args.size());
        for (const auto &arg : args)
            values.push_back(std::get<double>(arg));
        return perform_variadic_op(m_code, values);
    }

    // Mixed-type logic: iteratively apply the operation
    TrialValue accumulator = args[0];
    for (size_t i = 1; i < args.size(); ++i)
    {
        accumulator = std::visit(ElementWiseVisitor{m_code}, accumulator, args[i]);
    }
    return accumulator;
}

AddOperation::AddOperation() : VariadicBaseOperation(OpCode::ADD) {}
SubtractOperation::SubtractOperation() : VariadicBaseOperation(OpCode::SUBTRACT) {}
MultiplyOperation::MultiplyOperation() : VariadicBaseOperation(OpCode::MULTIPLY) {}
DivideOperation::DivideOperation() : VariadicBaseOperation(OpCode::DIVIDE) {}
PowerOperation::PowerOperation() : VariadicBaseOperation(OpCode::POWER) {}

TrialValue LogOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("LogOperation requires 1 argument.");
    return std::log(std::get<double>(args[0]));
}

TrialValue Log10Operation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Log10Operation requires 1 argument.");
    return std::log10(std::get<double>(args[0]));
}

TrialValue ExpOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("ExpOperation requires 1 argument.");
    return std::exp(std::get<double>(args[0]));
}

TrialValue SinOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("SinOperation requires 1 argument.");
    return std::sin(std::get<double>(args[0]));
}

TrialValue CosOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("CosOperation requires 1 argument.");
    return std::cos(std::get<double>(args[0]));
}

TrialValue TanOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("TanOperation requires 1 argument.");
    return std::tan(std::get<double>(args[0]));
}

TrialValue IdentityOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("IdentityOperation requires exactly one argument.");
    return args[0];
}

TrialValue GrowSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw std::runtime_error("GrowSeriesOperation requires 3 arguments.");
    double base_val = std::get<double>(args[0]);
    double growth_rate = std::get<double>(args[1]);
    int num_years = static_cast<int>(std::get<double>(args[2]));

    std::vector<double> series;
    series.reserve(num_years);
    double current_val = base_val;
    for (int i = 0; i < num_years; ++i)
    {
        current_val *= (1.0 + growth_rate);
        series.push_back(current_val);
    }
    return series;
}

TrialValue CompoundSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("CompoundSeriesOperation requires 2 arguments.");
    double base_val = std::get<double>(args[0]);
    const auto &growth_rates = std::get<std::vector<double>>(args[1]);

    std::vector<double> series;
    series.reserve(growth_rates.size());
    double current_val = base_val;
    for (const auto &rate : growth_rates)
    {
        current_val *= (1.0 + rate);
        series.push_back(current_val);
    }
    return series;
}

TrialValue NpvOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("NpvOperation requires 2 arguments.");
    double rate = std::get<double>(args[0]);
    const auto &cashflows = std::get<std::vector<double>>(args[1]);
    double npv = 0.0;
    for (size_t i = 0; i < cashflows.size(); ++i)
    {
        npv += cashflows[i] / std::pow(1.0 + rate, i + 1);
    }
    return npv;
}

TrialValue SumSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("SumSeriesOperation requires 1 argument.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    return std::accumulate(series.begin(), series.end(), 0.0);
}

TrialValue GetElementOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("GetElementOperation requires 2 arguments.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    int index = static_cast<int>(std::get<double>(args[1]));
    if (series.empty())
        throw std::runtime_error("Cannot get element from empty series.");
    if (index < 0)
        index = static_cast<int>(series.size()) + index;
    if (index < 0 || static_cast<size_t>(index) >= series.size())
        throw std::runtime_error("Index out of bounds.");
    return series[static_cast<size_t>(index)];
}

TrialValue SeriesDeltaOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("SeriesDeltaOperation requires 1 argument.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    if (series.empty())
        return std::vector<double>{};
    std::vector<double> delta_series;
    delta_series.reserve(series.size() - 1);
    for (size_t i = 1; i < series.size(); ++i)
    {
        delta_series.push_back(series[i] - series[i - 1]);
    }
    return delta_series;
}

TrialValue ComposeVectorOperation::execute(const std::vector<TrialValue> &args) const
{
    std::vector<double> composed_vector;
    composed_vector.reserve(args.size());
    for (const auto &arg_variant : args)
    {
        composed_vector.push_back(std::get<double>(arg_variant));
    }
    return composed_vector;
}

TrialValue InterpolateSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw std::runtime_error("InterpolateSeriesOperation requires 3 arguments.");

    double start_value = std::get<double>(args[0]);
    double end_value = std::get<double>(args[1]);
    int num_years = static_cast<int>(std::get<double>(args[2]));

    if (num_years < 1)
        return std::vector<double>{};
    if (num_years == 1)
        return std::vector<double>{end_value};

    std::vector<double> series;
    series.reserve(num_years);
    double total_diff = end_value - start_value;
    double step = total_diff / (num_years - 1);

    for (int i = 0; i < num_years; ++i)
    {
        series.push_back(start_value + i * step);
    }
    return series;
}

TrialValue CapitalizeExpenseOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
    {
        throw std::runtime_error("CapitalizeExpenseOperation requires 3 arguments: current_expense (scalar), past_expenses (vector), and amortization_period (scalar).");
    }

    double current_expense = std::get<double>(args[0]);
    const auto &past_expenses = std::get<std::vector<double>>(args[1]);
    int period = static_cast<int>(std::get<double>(args[2]));

    if (period <= 0)
    {
        throw std::runtime_error("Amortization period must be positive.");
    }

    double research_asset = 0.0;
    double amortization_this_year = 0.0;

    research_asset += current_expense;

    for (size_t i = 0; i < past_expenses.size(); ++i)
    {
        int year_ago = i + 1;
        if (year_ago < period)
        {
            research_asset += past_expenses[i] * (static_cast<double>(period - year_ago) / period);
        }
    }

    for (size_t i = 0; i < past_expenses.size(); ++i)
    {
        int year_ago = i + 1;
        if (year_ago <= period)
        {
            amortization_this_year += past_expenses[i] / period;
        }
    }

    return std::vector<double>{research_asset, amortization_this_year};
}

// This struct will hold the fully parsed CSV data in a standard, random-access format.
// We are storing the data itself, not the library's proxy objects.
struct CachedCsv
{
    std::vector<std::string> header;
    // Each row is a map from column name (string) to cell value (string).
    std::vector<std::unordered_map<std::string, std::string>> data;
};

// The cache maps a file path to a shared pointer to our fully parsed data structure.
static std::unordered_map<std::string, std::shared_ptr<CachedCsv>> g_csv_cache;

// Helper function to get the parsed CSV data, using the cache.
// This function reads the file only ONCE and stores it in our random-access-friendly format.
static std::shared_ptr<CachedCsv> get_cached_csv(const std::string &file_path)
{
    // If it's already in the cache, return the cached data immediately.
    if (g_csv_cache.count(file_path))
    {
        return g_csv_cache.at(file_path);
    }

    // If not in the cache, read and parse the file.
    try
    {
        csv::CSVReader reader(file_path);
        auto cached_data = std::make_shared<CachedCsv>();
        cached_data->header = reader.get_col_names();

        // Iterate through the reader to populate our own data structure.
        for (const auto &row : reader)
        {
            std::unordered_map<std::string, std::string> current_row_data;
            for (const auto &col_name : cached_data->header)
            {
                // Convert the cell's value to a std::string for permanent storage.
                current_row_data[col_name] = row[col_name].get<>();
            }
            cached_data->data.push_back(current_row_data);
        }

        // Store the newly parsed data in the cache and return it.
        g_csv_cache[file_path] = cached_data;
        return cached_data;
    }
    catch (const std::exception &e)
    {
        throw std::runtime_error("Failed to read or parse CSV file '" + file_path + "'. Error: " + e.what());
    }
}

TrialValue ReadCsvVectorOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("ReadCsvVectorOperation requires 2 arguments: file_path (string), column_name (string).");

    const std::string &file_path = std::get<std::string>(args[0]);
    const std::string &column_name = std::get<std::string>(args[1]);

    auto cached_data = get_cached_csv(file_path);

    // Check if the column name exists for a clear error message.
    bool column_exists = false;
    for (const auto &h : cached_data->header)
    {
        if (h == column_name)
        {
            column_exists = true;
            break;
        }
    }
    if (!column_exists)
    {
        throw std::runtime_error("Column '" + column_name + "' not found in file '" + file_path + "'.");
    }

    std::vector<double> column_vector;
    column_vector.reserve(cached_data->data.size());
    try
    {
        for (const auto &row_map : cached_data->data)
        {
            // Convert the stored string value to a double.
            column_vector.push_back(std::stod(row_map.at(column_name)));
        }
    }
    catch (const std::exception &e)
    {
        throw std::runtime_error("Error converting data to number in column '" + column_name + "' from file '" + file_path + "'. Please check for non-numeric values. Error: " + e.what());
    }
    return column_vector;
}

TrialValue ReadCsvScalarOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw std::runtime_error("ReadCsvScalarOperation requires 3 arguments: file_path (string), column_name (string), row_index (scalar).");

    const std::string &file_path = std::get<std::string>(args[0]);
    const std::string &column_name = std::get<std::string>(args[1]);
    int row_index = static_cast<int>(std::get<double>(args[2]));

    auto cached_data = get_cached_csv(file_path);
    double cell_value;

    // Perform bounds checking first.
    if (static_cast<size_t>(row_index) >= cached_data->data.size())
    {
        throw std::runtime_error("Row index " + std::to_string(row_index) + " is out of bounds for file '" + file_path + "' (File has " + std::to_string(cached_data->data.size()) + " data rows).");
    }

    // Now safely access the row by index.
    const auto &row_map = cached_data->data[row_index];

    try
    {
        // Check if the column exists in this row's map.
        const auto &cell_it = row_map.find(column_name);
        if (cell_it == row_map.end())
        {
            throw std::runtime_error("Column '" + column_name + "' not found in file '" + file_path + "'.");
        }
        // Convert the stored string value to a double.
        cell_value = std::stod(cell_it->second);
    }
    catch (const std::exception &e)
    {
        throw std::runtime_error("Error converting data to number at row " + std::to_string(row_index) + ", column '" + column_name + "' in file '" + file_path + "'. Error: " + e.what());
    }

    return cell_value;
}