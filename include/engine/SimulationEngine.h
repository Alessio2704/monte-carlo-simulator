#pragma once

#include "engine/datastructures.h"
#include "engine/IExecutionStep.h"
#include "engine/IExecutable.h"
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
    void build_execution_steps();
    void run_batch(int num_trials, std::vector<TrialValue> &results, std::exception_ptr &out_exception);

    void build_executable_factory();
    std::unordered_map<std::string, std::function<std::unique_ptr<IExecutable>()>> m_executable_factory;

    SimulationRecipe m_recipe;
    std::vector<std::unique_ptr<IExecutionStep>> m_execution_steps;
};