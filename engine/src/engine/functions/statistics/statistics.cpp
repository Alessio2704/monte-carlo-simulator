#include "include/engine/functions/statistics/samplers.h"
#include "include/engine/core/EngineException.h"
#include <random>
#include <stdexcept>
#include <cmath>

// --- Registration Function ---

void register_statistics_functions(FunctionRegistry &registry)
{
    registry.register_function("Normal", []
                               { return std::make_unique<NormalSampler>(); });
    registry.register_function("Uniform", []
                               { return std::make_unique<UniformSampler>(); });
    registry.register_function("Bernoulli", []
                               { return std::make_unique<BernoulliSampler>(); });
    registry.register_function("Lognormal", []
                               { return std::make_unique<LognormalSampler>(); });
    registry.register_function("Beta", []
                               { return std::make_unique<BetaSampler>(); });
    registry.register_function("Pert", []
                               { return std::make_unique<PertSampler>(); });
    registry.register_function("Triangular", []
                               { return std::make_unique<TriangularSampler>(); });
}

// --- Implementations (from original samplers.cpp) ---

// Helper to provide a thread-safe random number generator.
// Each thread will have its own generator instance.
inline std::mt19937 &get_thread_local_generator()
{
    static thread_local std::mt19937 generator(std::random_device{}());
    return generator;
}

std::vector<TrialValue> NormalSampler::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'Normal' requires 2 arguments: mean, stddev.");
    double mean = std::get<double>(args[0]);
    double stddev = std::get<double>(args[1]);
    std::normal_distribution<> dist(mean, stddev);
    return {dist(get_thread_local_generator())};
}

std::vector<TrialValue> UniformSampler::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'Uniform' requires 2 arguments: min, max.");
    double min = std::get<double>(args[0]);
    double max = std::get<double>(args[1]);
    std::uniform_real_distribution<> dist(min, max);
    return {dist(get_thread_local_generator())};
}

std::vector<TrialValue> BernoulliSampler::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'Bernoulli' requires 1 argument: p.");
    double p = std::get<double>(args[0]);
    std::bernoulli_distribution dist(p);
    return {static_cast<double>(dist(get_thread_local_generator()))};
}

std::vector<TrialValue> LognormalSampler::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'Lognormal' requires 2 arguments: log_mean, log_stddev.");
    double log_mean = std::get<double>(args[0]);
    double log_stddev = std::get<double>(args[1]);
    std::lognormal_distribution<> dist(log_mean, log_stddev);
    return {dist(get_thread_local_generator())};
}

std::vector<TrialValue> BetaSampler::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'Beta' requires 2 arguments: alpha, beta.");
    double alpha = std::get<double>(args[0]);
    double beta = std::get<double>(args[1]);
    if (alpha <= 0 || beta <= 0)
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Beta distribution parameters must be positive.");

    std::gamma_distribution<> gamma1(alpha, 1.0);
    std::gamma_distribution<> gamma2(beta, 1.0);

    double g1 = gamma1(get_thread_local_generator());
    double g2 = gamma2(get_thread_local_generator());

    if (g1 + g2 == 0.0)
        return {0.0};

    double result = g1 / (g1 + g2);
    return {result};
}

std::vector<TrialValue> PertSampler::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'Pert' requires 3 arguments: min, mostLikely, max.");
    double min = std::get<double>(args[0]);
    double mostLikely = std::get<double>(args[1]);
    double max = std::get<double>(args[2]);

    if (min > mostLikely || mostLikely > max || min == max)
    {
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Invalid PERT parameters: must be min <= mostLikely <= max and min != max.");
    }

    const double gamma = 4.0;
    double alpha = 1.0 + gamma * (mostLikely - min) / (max - min);
    double beta_param = 1.0 + gamma * (max - mostLikely) / (max - min);

    std::gamma_distribution<> gamma1(alpha, 1.0);
    std::gamma_distribution<> gamma2(beta_param, 1.0);
    double g1 = gamma1(get_thread_local_generator());
    double g2 = gamma2(get_thread_local_generator());

    double betaSample = (g1 + g2 == 0.0) ? 0.0 : g1 / (g1 + g2);
    double result = min + betaSample * (max - min);
    return {result};
}

std::vector<TrialValue> TriangularSampler::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 3)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'Triangular' requires 3 arguments: min, mostLikely, max.");
    double min = std::get<double>(args[0]);
    double mostLikely = std::get<double>(args[1]);
    double max = std::get<double>(args[2]);

    if (min > mostLikely || mostLikely > max)
    {
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Invalid Triangular parameters: must be min <= mostLikely <= max.");
    }

    std::uniform_real_distribution<> uniform_dist(0.0, 1.0);
    double u = uniform_dist(get_thread_local_generator());
    double fc = (mostLikely - min) / (max - min);
    double result;

    if (u < fc)
    {
        result = min + std::sqrt(u * (max - min) * (mostLikely - min));
    }
    else
    {
        result = max - std::sqrt((1 - u) * (max - min) * (max - mostLikely));
    }

    return {result};
}