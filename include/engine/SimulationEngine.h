#pragma once

#include "engine/datastructures.h"
#include <string>
#include <vector>
#include <unordered_map>
#include "engine/IOperation.h"

using TrialContext = std::unordered_map<std::string, TrialValue>;

class SimulationEngine
{
public:
    explicit SimulationEngine(const std::string &json_recipe_path);
    std::vector<TrialValue> run();

private:
    void parse_recipe();
    TrialValue resolve_value(const json &arg, TrialContext &context);
    void run_batch(int num_trials_for_thread, std::vector<TrialValue>& thread_results, std::exception_ptr& out_exception);
    void create_distribution_from_input(const std::string &name, const InputVariable &var);

    std::unordered_map<OpCode, std::unique_ptr<IOperation>> m_operations;

    SimulationRecipe m_recipe;
    std::string m_recipe_path;
};