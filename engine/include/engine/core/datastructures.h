#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <variant>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using TrialValue = std::variant<double, std::vector<double>, std::string>;

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
    COMPOUND_SERIES,
    COMPOSE_VECTOR,
    INTERPOLATE_SERIES,
    CAPITALIZE_EXPENSE,
    IDENTITY // For variable-to-variable assignment
};

// Represents a step like: `let x = 123.45` or `let y = [1, 2]`
struct LiteralAssignmentDef
{
    std::string result_name;
    TrialValue value; // The literal value is stored directly
};

// Represents a step like: `let x = add(y, z)` or `let s = Normal(m, s)`
struct ExecutionAssignmentDef
{
    std::string result_name;
    std::string function_name; // e.g., "add", "Normal", "Pert"
    std::vector<json> args;    // Raw arguments to be resolved at runtime
};

// A definition for any step in the execution sequence
using ExecutionStepDef = std::variant<LiteralAssignmentDef, ExecutionAssignmentDef>;

struct SimulationRecipe
{
    int num_trials = 1000;
    std::string output_variable;
    std::vector<ExecutionStepDef> pre_trial_steps;   // Steps to run once before simulation.
    std::vector<ExecutionStepDef> per_trial_steps;   // Steps to run for each trial.
    std::string output_file_path;
};