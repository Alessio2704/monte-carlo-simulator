#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <variant>
#include <nlohmann/json.hpp>
#include "distributions/IDistribution.h"

using json = nlohmann::json;
using TrialValue = std::variant<double, std::vector<double>>;
using DistributionParams = std::unordered_map<std::string, double>;

struct InputVariable
{
    std::string type;
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
    POWER,
    LOG,
    LOG10,
    EXP,
    SIN,
    COS,
    TAN,
    GROW_SERIES,
    NPV,
    SUM_SERIES
};

enum class DistributionType
{
    Normal,
    Pert,
    Uniform,
    Lognormal,
    Triangular,
    Bernoulli,
    Beta
};

struct Operation
{
    OpCode op_code;
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