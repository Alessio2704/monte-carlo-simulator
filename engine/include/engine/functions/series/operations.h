#pragma once
#include "include/engine/core/IExecutable.h"
#include "include/engine/functions/FunctionRegistry.h"

// --- Registration ---
void register_series_functions(FunctionRegistry &registry);

// --- Concrete Operation Classes ---
class GrowSeriesOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class CompoundSeriesOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class NpvOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class SumSeriesOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class GetElementOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class DeleteElementOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class SeriesDeltaOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class ComposeVectorOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class InterpolateSeriesOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class CapitalizeExpenseOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};