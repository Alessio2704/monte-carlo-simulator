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
    TrialValue value;
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
    SUM_SERIES,
    GET_ELEMENT,
    SERIES_DELTA,
    COMPOUND_SERIES, // Takes base_value (scalar) and vector_of_growth_rates (vector)
    COMPOSE_VECTOR,
    INTERPOLATE_SERIES,
    CAPITALIZE_EXPENSE,

    // Add a sentinel value at the very end.
    // ADD OTHER CODES ABOVE THIS ONE
    // Its integer value will automatically be the total number of real opcodes.
    _NUM_OPCODES
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