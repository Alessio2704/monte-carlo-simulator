#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <nlohmann/json.hpp>
#include "distributions/IDistribution.h"

using json = nlohmann::json;

using DistributionParams = std::unordered_map<std::string, double>;

struct InputVariable
{
    std::string type; // "fixed" or "distribution"

    double fixed_value = 0.0;

    std::string dist_name;
    DistributionParams dist_params;
};

enum class OpCode
{
    ADD,
    MULTIPLY,
    SUBTRACT,
    DIVIDE,
    POWER, // e.g., pow(base, exponent)
    LOG,   // Natural logarithm
    LOG10, // Base-10 logarithm
    EXP,   // e^x
    SIN,
    COS,
    TAN,
    UNKNOWN
};

enum class DistributionType
{
    Normal,
    Pert,
    Uniform,
    Lognormal,
    Triangular,
    Bernoulli,
    Beta,
    Unknown
};

struct Operation
{
    OpCode op_code = OpCode::UNKNOWN;
    std::vector<json> args;
    std::string result_name;
};

struct SimulationRecipe
{
    int num_trials = 1000;
    std::unordered_map<std::string, InputVariable> inputs;
    std::vector<Operation> operations;
    std::string output_variable;
    std::unordered_map<std::string, std::unique_ptr<IDistribution>> distributions;
};