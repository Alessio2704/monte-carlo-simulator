#pragma once

#include "engine/datastructures.h"
#include <string>
#include <vector>

class SimulationEngine
{
public:
    explicit SimulationEngine(const std::string &json_recipe_path);
    std::vector<double> run();

private:
    void parse_recipe();
    void create_distribution_from_input(const std::string &name, const InputVariable &var);
    double resolve_value(const json &arg, const std::unordered_map<std::string, double> &context);
    double evaluate_operation(const Operation &op, const std::unordered_map<std::string, double> &context);
    void run_batch(int num_trials_for_thread, std::vector<double> &thread_results);

    SimulationRecipe m_recipe;
    std::string m_recipe_path;
};