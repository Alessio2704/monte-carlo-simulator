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

    // This will be called by ExecutionStep objects to resolve their arguments.
    // It needs access to the factory, so it must be part of the engine.
    TrialValue resolve_value_recursively(const json &arg, const TrialContext &context) const;
    std::string get_output_file_path() const;

private:
    void parse_recipe(const std::string &path);
    void run_pre_trial_phase();
    void build_per_trial_steps();
    void run_batch(int num_trials, std::vector<TrialValue> &results, std::exception_ptr &out_exception);

    void build_executable_factory();
    std::unordered_map<std::string, std::function<std::unique_ptr<IExecutable>()>> m_executable_factory;

    SimulationRecipe m_recipe;
    TrialContext m_preloaded_context;
    std::vector<std::unique_ptr<IExecutionStep>> m_per_trial_steps;
};