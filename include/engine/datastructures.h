#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include "distributions/IDistribution.h"

// A struct to hold the parameters for a distribution.
using DistributionParams = std::unordered_map<std::string, double>;

// A struct to represent a single input variable from the JSON "inputs" block.
struct InputVariable
{
    std::string type; // "fixed" or "distribution"

    // --- Members for a "fixed" type ---
    double fixed_value = 0.0;

    // --- Members for a "distribution" type ---
    std::string dist_name; // "Normal", "PERT", etc.
    DistributionParams dist_params;
};

// Enum for all possible operations.
enum class OpCode
{
    ADD,
    MULTIPLY,
    SUBTRACT,
    DIVIDE,
    UNKNOWN
};

// Define an enum for all supported distribution types.
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

// Struct to represent a single calculation step.
struct Operation
{
    OpCode op_code = OpCode::UNKNOWN;
    std::vector<std::string> args;
    std::string result_name;
};

// Struct to hold the entire, parsed recipe.
struct SimulationRecipe
{
    int num_trials = 1000;
    std::unordered_map<std::string, InputVariable> inputs;
    std::vector<Operation> operations;
    std::string output_variable;
    std::unordered_map<std::string, std::unique_ptr<IDistribution>> distributions;
};