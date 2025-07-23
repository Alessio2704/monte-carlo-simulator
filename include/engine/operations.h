#pragma once

#include "engine/IOperation.h"
#include <stdexcept>
#include <cmath>
#include <numeric>
#include <variant>
#include <vector>

// --- Helper Visitor for Binary Operations ---
// This generic visitor contains the logic for all binary ops (ADD, SUBTRACT, etc.)
// to avoid duplicating the std::visit logic in every binary operation class.
struct BinaryOperationVisitor
{
    OpCode code; // The specific operation to perform

    // Overload for scalar op scalar
    TrialValue operator()(double val1, double val2) const
    {
        return perform_op(val1, val2);
    }
    // Overload for vector op scalar
    TrialValue operator()(const std::vector<double> &val1, double val2) const
    {
        std::vector<double> result;
        result.reserve(val1.size());
        for (double x : val1)
        {
            result.push_back(perform_op(x, val2));
        }
        return result;
    }
    // Overload for scalar op vector
    TrialValue operator()(double val1, const std::vector<double> &val2) const
    {
        std::vector<double> result;
        result.reserve(val2.size());
        for (double y : val2)
        {
            result.push_back(perform_op(val1, y));
        }
        return result;
    }
    // Overload for vector op vector
    TrialValue operator()(const std::vector<double> &val1, const std::vector<double> &val2) const
    {
        if (val1.size() != val2.size())
            throw std::runtime_error("Vector sizes must match for element-wise operations.");
        std::vector<double> result;
        result.reserve(val1.size());
        for (size_t i = 0; i < val1.size(); ++i)
        {
            result.push_back(perform_op(val1[i], val2[i]));
        }
        return result;
    }

private:
    // The actual scalar math logic
    double perform_op(double a, double b) const
    {
        switch (code)
        {
        case OpCode::ADD:
            return a + b;
        case OpCode::SUBTRACT:
            return a - b;
        case OpCode::MULTIPLY:
            return a * b;
        case OpCode::POWER:
            return std::pow(a, b);
        case OpCode::DIVIDE:
            if (b == 0.0)
                throw std::runtime_error("Division by zero");
            return a / b;
        default:
            throw std::logic_error("Internal error: Unsupported binary op in visitor");
        }
    }
};

// --- Concrete Binary Operation Classes ---

class AddOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::visit(BinaryOperationVisitor{OpCode::ADD}, args[0], args[1]);
    }
};

class SubtractOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::visit(BinaryOperationVisitor{OpCode::SUBTRACT}, args[0], args[1]);
    }
};

class MultiplyOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::visit(BinaryOperationVisitor{OpCode::MULTIPLY}, args[0], args[1]);
    }
};

class DivideOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::visit(BinaryOperationVisitor{OpCode::DIVIDE}, args[0], args[1]);
    }
};

class PowerOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::visit(BinaryOperationVisitor{OpCode::POWER}, args[0], args[1]);
    }
};

// --- Concrete Unary Math Operations ---

class LogOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::log(std::get<double>(args[0]));
    }
};

class Log10Operation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::log10(std::get<double>(args[0]));
    }
};

class ExpOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::exp(std::get<double>(args[0]));
    }
};

class SinOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::sin(std::get<double>(args[0]));
    }
};

class CosOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::cos(std::get<double>(args[0]));
    }
};

class TanOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        return std::tan(std::get<double>(args[0]));
    }
};

// --- Concrete Time-Series Operations ---

class GrowSeriesOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
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

class CompoundSeriesOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
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

class NpvOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
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

class SumSeriesOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        const auto &series = std::get<std::vector<double>>(args[0]);
        return std::accumulate(series.begin(), series.end(), 0.0);
    }
};

class GetElementOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
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

class SeriesDeltaOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
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

class ComposeVectorOperation : public IOperation
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


class InterpolateSeriesOperation : public IOperation
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        // We expect 3 scalar arguments: start, end, num_years
        if (args.size() != 3)
        {
            throw std::runtime_error("InterpolateSeriesOperation requires 3 arguments.");
        }

        double start_value = std::get<double>(args[0]);
        double end_value = std::get<double>(args[1]);
        int num_years = static_cast<int>(std::get<double>(args[2]));

        if (num_years < 2)
        {
            // Interpolation is only meaningful for 2 or more points.
            // For 1 year, the value is simply the end_value.
            return std::vector<double>{end_value};
        }

        std::vector<double> series;
        series.reserve(num_years);

        double total_diff = end_value - start_value;
        // The number of steps is num_years - 1. For a 10-year forecast, there are 9 steps.
        double step = total_diff / (num_years - 1);

        for (int i = 0; i < num_years; ++i)
        {
            series.push_back(start_value + i * step);
        }

        return series;
    }
};