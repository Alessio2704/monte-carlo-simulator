#pragma once

#include "engine/datastructures.h"
#include <string>
#include <vector>

// Forward declaration for TrialContext to avoid including the map header here
using TrialContext = std::unordered_map<std::string, TrialValue>;

class SimulationEngine
{
public:
    explicit SimulationEngine(const std::string &json_recipe_path);
    std::vector<double> run();

private:
    void parse_recipe();
    TrialValue resolve_value(const json &arg, const TrialContext &context);
    TrialValue evaluate_operation(const Operation &op, const TrialContext &context);

    void run_batch(int num_trials_for_thread, std::vector<double> &thread_results);
    void create_distribution_from_input(const std::string &name, const InputVariable &var);

    SimulationRecipe m_recipe;
    std::string m_recipe_path;
};