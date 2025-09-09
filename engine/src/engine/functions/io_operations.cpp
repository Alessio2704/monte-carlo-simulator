#include "include/engine/functions/operations.h"
#include "include/engine/core/EngineException.h"

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
        throw EngineException(EngineErrc::CsvFileNotFound, "Failed to read or parse CSV file '" + file_path + "'. Error: " + e.what());
    }
}
TrialValue ReadCsvVectorOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'read_csv_vector' requires 2 arguments.");
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
        throw EngineException(EngineErrc::CsvColumnNotFound, "Column '" + column_name + "' not found in file '" + file_path + "'.");
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
        throw EngineException(EngineErrc::CsvConversionError, "Error converting data to number in column '" + column_name + "' from file '" + file_path + "'. Please check for non-numeric values. Error: " + e.what());
    }
    return column_vector;
}
TrialValue ReadCsvScalarOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'read_csv_scalar' requires 3 arguments.");
    const std::string &file_path = std::get<std::string>(args[0]);
    const std::string &column_name = std::get<std::string>(args[1]);
    int row_index = static_cast<int>(std::get<double>(args[2]));
    auto cached_data = get_cached_csv(file_path);
    double cell_value;
    if (static_cast<size_t>(row_index) >= cached_data->data.size())
    {
        throw EngineException(EngineErrc::CsvRowIndexOutOfBounds, "Row index " + std::to_string(row_index) + " is out of bounds for file '" + file_path + "' (File has " + std::to_string(cached_data->data.size()) + " data rows).");
    }
    const auto &row_map = cached_data->data[row_index];
    try
    {
        const auto &cell_it = row_map.find(column_name);
        if (cell_it == row_map.end())
        {
            throw EngineException(EngineErrc::CsvColumnNotFound, "Column '" + column_name + "' not found in file '" + file_path + "'.");
        }
        cell_value = std::stod(cell_it->second);
    }
    catch (const std::exception &e)
    {
        throw EngineException(EngineErrc::CsvConversionError, "Error converting data to number at row " + std::to_string(row_index) + ", column '" + column_name + "' in file '" + file_path + "'. Error: " + e.what());
    }
    return cell_value;
}