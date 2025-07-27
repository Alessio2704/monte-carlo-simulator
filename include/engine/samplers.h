#pragma once

#include "engine/IExecutable.h"
#include <random>
#include <stdexcept>
#include <cmath>
#include <numeric>
#include "datastructures.h"

// Helper to provide a thread-safe random number generator.
// Each thread will have its own generator instance.
inline std::mt19937 &get_thread_local_generator()
{
    static thread_local std::mt19937 generator(std::random_device{}());
    return generator;
}

class NormalSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 2)
            throw std::runtime_error("NormalSampler requires 2 arguments: mean, stddev.");
        double mean = std::get<double>(args[0]);
        double stddev = std::get<double>(args[1]);
        std::normal_distribution<> dist(mean, stddev);
        return dist(get_thread_local_generator());
    }
};

class UniformSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 2)
            throw std::runtime_error("UniformSampler requires 2 arguments: min, max.");
        double min = std::get<double>(args[0]);
        double max = std::get<double>(args[1]);
        std::uniform_real_distribution<> dist(min, max);
        return dist(get_thread_local_generator());
    }
};

class BernoulliSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 1)
            throw std::runtime_error("BernoulliSampler requires 1 argument: p.");
        double p = std::get<double>(args[0]);
        std::bernoulli_distribution dist(p);
        return static_cast<double>(dist(get_thread_local_generator()));
    }
};

class LognormalSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 2)
            throw std::runtime_error("LognormalSampler requires 2 arguments: log_mean, log_stddev.");
        double log_mean = std::get<double>(args[0]);
        double log_stddev = std::get<double>(args[1]);
        std::lognormal_distribution<> dist(log_mean, log_stddev);
        return dist(get_thread_local_generator());
    }
};

class BetaSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 2)
            throw std::runtime_error("BetaSampler requires 2 arguments: alpha, beta.");
        double alpha = std::get<double>(args[0]);
        double beta = std::get<double>(args[1]);
        if (alpha <= 0 || beta <= 0)
            throw std::invalid_argument("Beta distribution parameters must be positive.");

        std::gamma_distribution<> gamma1(alpha, 1.0);
        std::gamma_distribution<> gamma2(beta, 1.0);

        double g1 = gamma1(get_thread_local_generator());
        double g2 = gamma2(get_thread_local_generator());

        if (g1 + g2 == 0.0)
            return 0.0;
        return g1 / (g1 + g2);
    }
};

class PertSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 3)
            throw std::runtime_error("PertSampler requires 3 arguments: min, mostLikely, max.");
        double min = std::get<double>(args[0]);
        double mostLikely = std::get<double>(args[1]);
        double max = std::get<double>(args[2]);

        if (min > mostLikely || mostLikely > max || min == max)
        {
            throw std::invalid_argument("Invalid PERT parameters: must be min <= mostLikely <= max and min != max.");
        }

        const double gamma = 4.0;
        double alpha = 1.0 + gamma * (mostLikely - min) / (max - min);
        double beta_param = 1.0 + gamma * (max - mostLikely) / (max - min);

        BetaSampler beta_sampler;
        double betaSample = std::get<double>(beta_sampler.execute({TrialValue(alpha), TrialValue(beta_param)}));
        return min + betaSample * (max - min);
    }
};

class TriangularSampler : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override
    {
        if (args.size() != 3)
            throw std::runtime_error("TriangularSampler requires 3 arguments: min, mostLikely, max.");
        double min = std::get<double>(args[0]);
        double mostLikely = std::get<double>(args[1]);
        double max = std::get<double>(args[2]);

        if (min > mostLikely || mostLikely > max)
        {
            throw std::invalid_argument("Invalid Triangular parameters: must be min <= mostLikely <= max.");
        }

        std::uniform_real_distribution<> uniform_dist(0.0, 1.0);
        double u = uniform_dist(get_thread_local_generator());
        double fc = (mostLikely - min) / (max - min);

        if (u < fc)
        {
            return min + std::sqrt(u * (max - min) * (mostLikely - min));
        }
        else
        {
            return max - std::sqrt((1 - u) * (max - min) * (max - mostLikely));
        }
    }
};