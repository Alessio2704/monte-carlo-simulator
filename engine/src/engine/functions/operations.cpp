#include "include/engine/functions/operations.h"
#include <stdexcept>
#include <cmath>
#include <numeric>
#include <variant>
#include <vector>
#include <memory>

// The csv.hpp header from the csv-parser library generates some warnings on MSVC
// with high warning levels. We will temporarily disable the specific warning (C4127)
// just for the inclusion of this header.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4127) // C4127: conditional expression is constant
#endif

#include "csv.hpp"

#ifdef _MSC_VER
#pragma warning(pop)
#endif

// =====================================================================================
// == SIMD-FRIENDLY "FAST PATH" HELPERS
// =====================================================================================
// These simple, standalone functions contain loops that modern C++ compilers
// can easily auto-vectorize into high-performance SIMD instructions (e.g., AVX, SSE).

// --- Vector-Vector Operations ---
inline std::vector<double> add_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = left[i] + right[i];
    }
    return result;
}
inline std::vector<double> subtract_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = left[i] - right[i];
    }
    return result;
}
inline std::vector<double> multiply_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = left[i] * right[i];
    }
    return result;
}
inline std::vector<double> divide_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        if (right[i] == 0.0)
            throw std::runtime_error("Division by zero in vector operation.");
        result[i] = left[i] / right[i];
    }
    return result;
}
inline std::vector<double> power_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = std::pow(left[i], right[i]);
    }
    return result;
}

// --- Vector-Scalar Operations ---
inline std::vector<double> add_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] + scalar;
    }
    return result;
}
inline std::vector<double> subtract_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] - scalar;
    }
    return result;
}
inline std::vector<double> multiply_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] * scalar;
    }
    return result;
}
inline std::vector<double> divide_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    if (scalar == 0.0)
        throw std::runtime_error("Division by zero.");
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] / scalar;
    }
    return result;
}
inline std::vector<double> power_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = std::pow(vec[i], scalar);
    }
    return result;
}

// --- Scalar-Vector Operations ---
inline std::vector<double> add_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = scalar + vec[i];
    }
    return result;
}
inline std::vector<double> subtract_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = scalar - vec[i];
    }
    return result;
}
inline std::vector<double> multiply_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = scalar * vec[i];
    }
    return result;
}
inline std::vector<double> divide_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        if (vec[i] == 0.0)
            throw std::runtime_error("Division by zero.");
        result[i] = scalar / vec[i];
    }
    return result;
}
inline std::vector<double> power_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = std::pow(scalar, vec[i]);
    }
    return result;
}

// =====================================================================================
// == GENERIC "SLOW PATH" HELPERS
// =====================================================================================

inline double perform_variadic_op(OpCode code, const std::vector<double> &values)
{
    if (values.empty())
        throw std::runtime_error("Cannot perform operation on an empty list of values.");
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

struct ElementWiseVisitor
{
    OpCode code;
    TrialValue operator()(double left, double right) const { return perform_variadic_op(code, {left, right}); }
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
    TrialValue operator()(const std::vector<double> &vec_left, const std::vector<double> &vec_right) const
    {
        if (vec_left.size() != vec_right.size())
            throw std::runtime_error("Vector size mismatch: element-wise operation requires vectors of the same length, but got sizes " + std::to_string(vec_left.size()) + " and " + std::to_string(vec_right.size()) + ".");
        std::vector<double> result;
        result.reserve(vec_left.size());
        for (size_t i = 0; i < vec_left.size(); ++i)
        {
            result.push_back(perform_variadic_op(code, {vec_left[i], vec_right[i]}));
        }
        return result;
    }
    template <typename T>
    TrialValue operator()(const std::string &, T) const { throw std::logic_error("Mathematical operations on strings are not supported."); }
    template <typename T>
    TrialValue operator()(T, const std::string &) const { throw std::logic_error("Mathematical operations on strings are not supported."); }
    TrialValue operator()(const std::string &, const std::string &) const { throw std::logic_error("Mathematical operations on strings are not supported."); }
};

// =====================================================================================
// == IExecutable Implementations with Fast Path Dispatcher
// =====================================================================================

VariadicBaseOperation::VariadicBaseOperation(OpCode code) : m_code(code) {}

TrialValue VariadicBaseOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.empty())
        throw std::runtime_error("Operation requires at least one argument.");
    if (args.size() == 1)
        return args[0];

    // --- FAST PATH DISPATCHER ---
    if (args.size() == 2)
    {
        const auto &left = args[0];
        const auto &right = args[1];

        if (std::holds_alternative<std::vector<double>>(left) && std::holds_alternative<std::vector<double>>(right))
        {
            const auto &vec_left = std::get<std::vector<double>>(left);
            const auto &vec_right = std::get<std::vector<double>>(right);
            if (vec_left.size() != vec_right.size())
                throw std::runtime_error("Vector size mismatch: element-wise operation requires vectors of the same length, but got sizes " + std::to_string(vec_left.size()) + " and " + std::to_string(vec_right.size()) + ".");

            switch (m_code)
            {
            case OpCode::ADD:
                return add_vectors_simd(vec_left, vec_right);
            case OpCode::SUBTRACT:
                return subtract_vectors_simd(vec_left, vec_right);
            case OpCode::MULTIPLY:
                return multiply_vectors_simd(vec_left, vec_right);
            case OpCode::DIVIDE:
                return divide_vectors_simd(vec_left, vec_right);
            case OpCode::POWER:
                return power_vectors_simd(vec_left, vec_right);
            default:
                break; // Fall through for any other op code
            }
        }
        else if (std::holds_alternative<std::vector<double>>(left) && std::holds_alternative<double>(right))
        {
            const auto &vec = std::get<std::vector<double>>(left);
            double scalar = std::get<double>(right);
            switch (m_code)
            {
            case OpCode::ADD:
                return add_vector_scalar_simd(vec, scalar);
            case OpCode::SUBTRACT:
                return subtract_vector_scalar_simd(vec, scalar);
            case OpCode::MULTIPLY:
                return multiply_vector_scalar_simd(vec, scalar);
            case OpCode::DIVIDE:
                return divide_vector_scalar_simd(vec, scalar);
            case OpCode::POWER:
                return power_vector_scalar_simd(vec, scalar);
            default:
                break;
            }
        }
        else if (std::holds_alternative<double>(left) && std::holds_alternative<std::vector<double>>(right))
        {
            double scalar = std::get<double>(left);
            const auto &vec = std::get<std::vector<double>>(right);
            switch (m_code)
            {
            case OpCode::ADD:
                return add_scalar_vector_simd(scalar, vec);
            case OpCode::SUBTRACT:
                return subtract_scalar_vector_simd(scalar, vec);
            case OpCode::MULTIPLY:
                return multiply_scalar_vector_simd(scalar, vec);
            case OpCode::DIVIDE:
                return divide_scalar_vector_simd(scalar, vec);
            case OpCode::POWER:
                return power_scalar_vector_simd(scalar, vec);
            default:
                break;
            }
        }
    }

    // --- SLOW PATH (FALLBACK) ---
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
        throw std::runtime_error("Function 'log' requires 1 argument.");
    return std::log(std::get<double>(args[0]));
}
TrialValue Log10Operation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'log10' requires 1 argument.");
    return std::log10(std::get<double>(args[0]));
}
TrialValue ExpOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'exp' requires 1 argument.");
    return std::exp(std::get<double>(args[0]));
}
TrialValue SinOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'sin' requires 1 argument.");
    return std::sin(std::get<double>(args[0]));
}
TrialValue CosOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'cos' requires 1 argument.");
    return std::cos(std::get<double>(args[0]));
}
TrialValue TanOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'tan' requires 1 argument.");
    return std::tan(std::get<double>(args[0]));
}
TrialValue IdentityOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'identity' requires exactly 1 argument.");
    return args[0];
}
TrialValue GrowSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw std::runtime_error("Function 'grow_series' requires 3 arguments.");
    double base_val = std::get<double>(args[0]);
    double growth_rate = std::get<double>(args[1]);
    int num_years = static_cast<int>(std::get<double>(args[2]));

    std::vector<double> series;
    if (num_years < 1)
        return series;

    series.reserve(num_years);
    double current_val = base_val;
    double growth_factor = 1.0 + growth_rate;
    for (int i = 0; i < num_years; ++i)
    {
        current_val *= growth_factor;
        series.push_back(current_val);
    }
    return series;
}

TrialValue CompoundSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("Function 'compound_series' requires 2 arguments.");
    double base_val = std::get<double>(args[0]);
    const auto &growth_rates = std::get<std::vector<double>>(args[1]);

    std::vector<double> series(growth_rates.size()); // Pre-allocate
    double current_val = base_val;
    for (size_t i = 0; i < growth_rates.size(); ++i)
    {
        current_val *= (1.0 + growth_rates[i]);
        series[i] = current_val;
    }
    return series;
}

TrialValue NpvOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("Function 'npv' requires 2 arguments.");
    double rate = std::get<double>(args[0]);
    const auto &cashflows = std::get<std::vector<double>>(args[1]);

    double npv = 0.0;
    double discount_factor = 1.0 + rate;
    if (discount_factor == 0.0)
        throw std::runtime_error("Discount rate cannot be -100% (-1.0).");

    for (const auto &cashflow : cashflows)
    {
        npv += cashflow / discount_factor;
        discount_factor *= (1.0 + rate);
    }
    return npv;
}

TrialValue SumSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'sum_series' requires 1 argument.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    return std::accumulate(series.begin(), series.end(), 0.0);
}
TrialValue GetElementOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("Function 'get_element' requires 2 arguments.");
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
TrialValue DeleteElementOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw std::runtime_error("Function 'delete_element' requires 2 arguments.");
    const auto &input_vector = std::get<std::vector<double>>(args[0]);
    int index_to_delete = static_cast<int>(std::get<double>(args[1]));
    if (input_vector.empty())
        throw std::runtime_error("Cannot delete element from an empty vector.");
    if (index_to_delete < 0)
    {
        index_to_delete = static_cast<int>(input_vector.size()) + index_to_delete;
    }
    if (index_to_delete < 0 || static_cast<size_t>(index_to_delete) >= input_vector.size())
        throw std::runtime_error("Index out of bounds for delete_element operation.");
    std::vector<double> result_vector;
    result_vector.reserve(input_vector.size() - 1);
    for (size_t i = 0; i < input_vector.size(); ++i)
    {
        if (static_cast<int>(i) != index_to_delete)
        {
            result_vector.push_back(input_vector[i]);
        }
    }
    return result_vector;
}

TrialValue SeriesDeltaOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw std::runtime_error("Function 'series_delta' requires 1 argument.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    if (series.empty())
        return std::vector<double>{};

    std::vector<double> delta_series(series.size() - 1); // Pre-allocate
    for (size_t i = 0; i < delta_series.size(); ++i)
    {
        delta_series[i] = series[i + 1] - series[i];
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
        throw std::runtime_error("Function 'interpolate_series' requires 3 arguments.");
    double start_value = std::get<double>(args[0]);
    double end_value = std::get<double>(args[1]);
    int num_years = static_cast<int>(std::get<double>(args[2]));
    if (num_years < 1)
        return std::vector<double>{};
    if (num_years == 1)
        return std::vector<double>{end_value};

    std::vector<double> series(num_years); // Pre-allocate
    double total_diff = end_value - start_value;
    double step = total_diff / (num_years - 1);
    for (int i = 0; i < num_years; ++i)
    {
        series[i] = start_value + i * step;
    }
    return series;
}
TrialValue CapitalizeExpenseOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw std::runtime_error("Function 'capitalize_expense' requires 3 arguments.");
    double current_expense = std::get<double>(args[0]);
    const auto &past_expenses = std::get<std::vector<double>>(args[1]);
    int period = static_cast<int>(std::get<double>(args[2]));
    if (period <= 0)
        throw std::runtime_error("Amortization period must be positive.");
    double research_asset = 0.0;
    double amortization_this_year = 0.0;
    research_asset += current_expense;
    for (size_t i = 0; i < past_expenses.size(); ++i)
    {
        int year_ago = static_cast<int>(i) + 1;
        if (year_ago < period)
        {
            research_asset += past_expenses[i] * (static_cast<double>(period - year_ago) / period);
        }
    }
    for (size_t i = 0; i < past_expenses.size(); ++i)
    {
        int year_ago = static_cast<int>(i) + 1;
        if (year_ago <= period)
        {
            amortization_this_year += past_expenses[i] / period;
        }
    }
    return std::vector<double>{research_asset, amortization_this_year};
}

// --- CSV Reading ---
struct CachedCsv
{
    std::vector<std::string> header;
    std::vector<std::unordered_map<std::string, std::string>> data;
};
static std::unordered_map<std::string, std::shared_ptr<CachedCsv>> g_csv_cache;
static std::shared_ptr<CachedCsv> get_cached_csv(const std::string &file_path)
{
    if (g_csv_cache.count(file_path))
    {
        return g_csv_cache.at(file_path);
    }
    try
    {
        csv::CSVReader reader(file_path);
        auto cached_data = std::make_shared<CachedCsv>();
        cached_data->header = reader.get_col_names();
        for (const auto &row : reader)
        {
            std::unordered_map<std::string, std::string> current_row_data;
            for (const auto &col_name : cached_data->header)
            {
                current_row_data[col_name] = row[col_name].get<>();
            }
            cached_data->data.push_back(current_row_data);
        }
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
        throw std::runtime_error("Function 'read_csv_vector' requires 2 arguments.");
    const std::string &file_path = std::get<std::string>(args[0]);
    const std::string &column_name = std::get<std::string>(args[1]);
    auto cached_data = get_cached_csv(file_path);
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
        throw std::runtime_error("Function 'read_csv_scalar' requires 3 arguments.");
    const std::string &file_path = std::get<std::string>(args[0]);
    const std::string &column_name = std::get<std::string>(args[1]);
    int row_index = static_cast<int>(std::get<double>(args[2]));
    auto cached_data = get_cached_csv(file_path);
    double cell_value;
    if (static_cast<size_t>(row_index) >= cached_data->data.size())
    {
        throw std::runtime_error("Row index " + std::to_string(row_index) + " is out of bounds for file '" + file_path + "' (File has " + std::to_string(cached_data->data.size()) + " data rows).");
    }
    const auto &row_map = cached_data->data[row_index];
    try
    {
        const auto &cell_it = row_map.find(column_name);
        if (cell_it == row_map.end())
        {
            throw std::runtime_error("Column '" + column_name + "' not found in file '" + file_path + "'.");
        }
        cell_value = std::stod(cell_it->second);
    }
    catch (const std::exception &e)
    {
        throw std::runtime_error("Error converting data to number at row " + std::to_string(row_index) + ", column '" + column_name + "' in file '" + file_path + "'. Error: " + e.what());
    }
    return cell_value;
}