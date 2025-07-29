#pragma once

#include "engine/IExecutable.h"
#include <stdexcept>
#include <cmath>
#include <numeric>
#include <variant>
#include <vector>

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

    // Case 1: scalar op scalar
    TrialValue operator()(double left, double right) const
    {
        return perform_variadic_op(code, {left, right});
    }

    // Case 2: vector op scalar
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

    // Case 3: scalar op vector
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

    // Case 4: vector op vector
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
};

class VariadicBaseOperation : public IExecutable
{
public:
    explicit VariadicBaseOperation(OpCode code) : m_code(code) {}

    TrialValue execute(const std::vector<TrialValue> &args) const override
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

private:
    OpCode m_code;
};

class AddOperation : public VariadicBaseOperation
{
public:
    AddOperation() : VariadicBaseOperation(OpCode::ADD) {}
};
class SubtractOperation : public VariadicBaseOperation
{
public:
    SubtractOperation() : VariadicBaseOperation(OpCode::SUBTRACT) {}
};
class MultiplyOperation : public VariadicBaseOperation
{
public:
    MultiplyOperation() : VariadicBaseOperation(OpCode::MULTIPLY) {}
};
class DivideOperation : public VariadicBaseOperation
{
public:
    DivideOperation() : VariadicBaseOperation(OpCode::DIVIDE) {}
};
class PowerOperation : public VariadicBaseOperation
{
public:
    PowerOperation() : VariadicBaseOperation(OpCode::POWER) {}
};

class LogOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("LogOperation requires 1 argument.");
        return std::log(std::get<double>(args[0]));
    }
};

class Log10Operation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("Log10Operation requires 1 argument.");
        return std::log10(std::get<double>(args[0]));
    }
};

class ExpOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("ExpOperation requires 1 argument.");
        return std::exp(std::get<double>(args[0]));
    }
};

class SinOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("SinOperation requires 1 argument.");
        return std::sin(std::get<double>(args[0]));
    }
};

class CosOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("CosOperation requires 1 argument.");
        return std::cos(std::get<double>(args[0]));
    }
};

class TanOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("TanOperation requires 1 argument.");
        return std::tan(std::get<double>(args[0]));
    }
};

class IdentityOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("IdentityOperation requires exactly one argument.");
        return args[0];
    }
};

class GrowSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
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
};

class CompoundSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
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
};

class NpvOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
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
};

class SumSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("SumSeriesOperation requires 1 argument.");
        const auto &series = std::get<std::vector<double>>(args[0]);
        return std::accumulate(series.begin(), series.end(), 0.0);
    }
};

class GetElementOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
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
};

class SeriesDeltaOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("SeriesDeltaOperation requires 1 argument.");
        const auto &series = std::get<std::vector<double>>(args[0]);
        if (series.empty())
            return std::vector<double>{};
        std::vector<double> delta_series;
        delta_series.reserve(series.size());
        delta_series.push_back(0.0);
        for (size_t i = 1; i < series.size(); ++i)
        {
            delta_series.push_back(series[i] - series[i - 1]);
        }
        return delta_series;
    }
};

class ComposeVectorOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        std::vector<double> composed_vector;
        composed_vector.reserve(args.size());
        for (const auto &arg_variant : args)
        {
            composed_vector.push_back(std::get<double>(arg_variant));
        }
        return composed_vector;
    }
};

class InterpolateSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
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
};

class CapitalizeExpenseOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
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
};