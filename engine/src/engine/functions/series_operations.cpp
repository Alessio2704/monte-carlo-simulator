#include "include/engine/functions/operations.h"
#include "include/engine/core/EngineException.h"
#include <vector>
#include <numeric>

// =====================================================================================
// == Vector and Series Operations
// =====================================================================================

TrialValue GrowSeriesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'grow_series' requires 3 arguments.");
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
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'compound_series' requires 2 arguments.");
    double base_val = std::get<double>(args[0]);
    const auto &growth_rates = std::get<std::vector<double>>(args[1]);
    std::vector<double> series(growth_rates.size());
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
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'npv' requires 2 arguments.");
    double rate = std::get<double>(args[0]);
    const auto &cashflows = std::get<std::vector<double>>(args[1]);
    double npv = 0.0;
    double discount_factor = 1.0 + rate;
    if (discount_factor == 0.0)
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Discount rate cannot be -100% (-1.0).");
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
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'sum_series' requires 1 argument.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    return std::accumulate(series.begin(), series.end(), 0.0);
}
TrialValue GetElementOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'get_element' requires 2 arguments.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    int index = static_cast<int>(std::get<double>(args[1]));
    if (series.empty())
        throw EngineException(EngineErrc::EmptyVectorOperation, "Cannot get element from empty series.");
    if (index < 0)
        index = static_cast<int>(series.size()) + index;
    if (index < 0 || static_cast<size_t>(index) >= series.size())
        throw EngineException(EngineErrc::IndexOutOfBounds, "Index out of bounds.");
    return series[static_cast<size_t>(index)];
}
TrialValue DeleteElementOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'delete_element' requires 2 arguments.");
    const auto &input_vector = std::get<std::vector<double>>(args[0]);
    int index_to_delete = static_cast<int>(std::get<double>(args[1]));
    if (input_vector.empty())
        throw EngineException(EngineErrc::EmptyVectorOperation, "Cannot delete element from an empty vector.");
    if (index_to_delete < 0)
    {
        index_to_delete = static_cast<int>(input_vector.size()) + index_to_delete;
    }
    if (index_to_delete < 0 || static_cast<size_t>(index_to_delete) >= input_vector.size())
        throw EngineException(EngineErrc::IndexOutOfBounds, "Index out of bounds for delete_element operation.");
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
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'series_delta' requires 1 argument.");
    const auto &series = std::get<std::vector<double>>(args[0]);
    if (series.empty())
        return std::vector<double>{};
    std::vector<double> delta_series(series.size() - 1);
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
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'interpolate_series' requires 3 arguments.");
    double start_value = std::get<double>(args[0]);
    double end_value = std::get<double>(args[1]);
    int num_years = static_cast<int>(std::get<double>(args[2]));
    if (num_years < 1)
        return std::vector<double>{};
    if (num_years == 1)
        return std::vector<double>{end_value};
    std::vector<double> series(num_years);
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
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'capitalize_expense' requires 3 arguments.");
    double current_expense = std::get<double>(args[0]);
    const auto &past_expenses = std::get<std::vector<double>>(args[1]);
    int period = static_cast<int>(std::get<double>(args[2]));
    if (period <= 0)
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Amortization period must be positive.");
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