#pragma once
#include "include/engine/core/IExecutable.h"
#include "include/engine/functions/FunctionRegistry.h"

// --- Registration ---
void register_statistics_functions(FunctionRegistry &registry);

// --- Concrete Sampler Classes ---
class NormalSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class UniformSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class BernoulliSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class LognormalSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class BetaSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class PertSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class TriangularSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};