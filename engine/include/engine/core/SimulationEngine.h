#pragma once

#include "include/engine/core/DataStructures.h"
#include "include/engine/core/IExecutionStep.h"
#include "include/engine/core/IExecutable.h"
#include "include/engine/functions/FunctionRegistry.h"
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <functional>

class SimulationEngine
{
public:
    explicit SimulationEngine(const std::string &json_recipe_path, bool is_preview = false);
    std::vector<TrialValue> run();
    std::string get_output_file_path() const;

private:
    void build_function_registry();
    void parse_and_build(const std::string &path);
    void run_pre_trial_phase();
    void run_batch(int num_trials, std::vector<TrialValue> &results, std::exception_ptr &out_exception);

    int m_num_trials;
    size_t m_output_variable_index;
    std::string m_output_file_path;
    bool m_is_preview;

    std::unique_ptr<FunctionRegistry> m_function_registry;
    const std::unordered_map<std::string, FunctionRegistry::FactoryFunc> *m_executable_factory;

    std::vector<TrialValue> m_preloaded_context_vector;
    std::vector<std::unique_ptr<IExecutionStep>> m_pre_trial_steps;
    std::vector<std::unique_ptr<IExecutionStep>> m_per_trial_steps;
};