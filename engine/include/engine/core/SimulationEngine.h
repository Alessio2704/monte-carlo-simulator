#pragma once

#include "include/engine/core/datastructures.h"
#include "include/engine/core/IExecutionStep.h"
#include "include/engine/core/IExecutable.h"
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <functional>

class SimulationEngine
{
public:
    explicit SimulationEngine(const std::string &json_recipe_path);
    std::vector<TrialValue> run();
    std::string get_output_file_path() const;

private:
    void parse_recipe(const std::string &path);
    void build_variable_registry(); // Analyzes the recipe to map all variable names to indices.
    void run_pre_trial_phase();
    void build_per_trial_steps();
    void run_batch(int num_trials, std::vector<TrialValue> &results, std::exception_ptr &out_exception);

    void build_executable_factory();
    std::unordered_map<std::string, std::function<std::unique_ptr<IExecutable>()>> m_executable_factory;

    SimulationRecipe m_recipe;

    std::unordered_map<std::string, size_t> m_variable_registry;

    std::vector<TrialValue> m_preloaded_context_vector;

    size_t m_output_variable_index;

    std::vector<std::unique_ptr<IExecutionStep>> m_per_trial_steps;
};