#include "include/engine/core/SimulationEngine.h"
#include "include/engine/core/ExecutionSteps.h"
#include "include/engine/core/EngineException.h"

// Include all the domain registration headers
#include "include/engine/functions/core/operations.h"
#include "include/engine/functions/series/operations.h"
#include "include/engine/functions/statistics/samplers.h"
#include "include/engine/functions/io/operations.h"
#include "include/engine/functions/financial/financial.h"
#include "include/engine/functions/epidemiology/epidemiology.h"

#include <nlohmann/json.hpp>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <thread>
#include <vector>

using json = nlohmann::json;

SimulationEngine::SimulationEngine(const std::string &json_recipe_path, bool is_preview)
    : m_is_preview(is_preview), m_executable_factory(nullptr)
{
    build_function_registry();
    parse_and_build(json_recipe_path);
    run_pre_trial_phase();
}

void SimulationEngine::build_function_registry()
{
    m_function_registry = std::make_unique<FunctionRegistry>();

    // Call each domain's registration function
    register_core_functions(*m_function_registry);
    register_series_functions(*m_function_registry);
    register_statistics_functions(*m_function_registry);
    register_io_functions(*m_function_registry);
    register_financial_functions(*m_function_registry);
    register_epidemiology_functions(*m_function_registry);

    // Get a pointer to the factory map for use during parsing
    m_executable_factory = &m_function_registry->get_factory_map();
}

std::string SimulationEngine::get_output_file_path() const
{
    return m_output_file_path;
}

void SimulationEngine::parse_and_build(const std::string &path)
{
    std::ifstream file_stream(path);
    if (!file_stream.is_open())
    {
        throw EngineException(EngineErrc::RecipeFileNotFound, "Failed to open recipe file: " + path);
    }
    json recipe_json;
    try
    {
        recipe_json = json::parse(file_stream);
    }
    catch (const json::parse_error &e)
    {
        throw EngineException(EngineErrc::RecipeParseError, "Failed to parse JSON recipe: " + std::string(e.what()));
    }

    try
    {
        const auto &config = recipe_json.at("simulation_config");
        m_num_trials = config.at("num_trials");
        m_output_variable_index = recipe_json.at("output_variable_index");
        if (config.contains("output_file") && config.at("output_file").is_string())
        {
            m_output_file_path = config.at("output_file").get<std::string>();
        }

        const size_t num_variables = recipe_json.at("variable_registry").size();
        if (m_output_variable_index >= num_variables && num_variables > 0)
        {
            throw EngineException(EngineErrc::IndexOutOfBounds, "Output variable index is out of bounds of the variable registry.");
        }
        m_preloaded_context_vector.resize(num_variables);

        auto build_step_from_json = [&](const json &step_json) -> std::unique_ptr<IExecutionStep>
        {
            std::string type = step_json.at("type");
            int line = step_json.value("line", -1);

            if (type == "literal_assignment")
            {
                size_t result_index = step_json.at("result");
                const auto &val_json = step_json.at("value");
                TrialValue value;
                if (val_json.is_array())
                {
                    value = val_json.get<std::vector<double>>();
                }
                else if (val_json.is_number())
                {
                    value = val_json.get<double>();
                }
                else if (val_json.is_boolean())
                {
                    value = val_json.get<bool>();
                }
                else if (val_json.is_string())
                {
                    value = val_json.get<std::string>();
                }
                else
                {
                    throw EngineException(EngineErrc::RecipeParseError, "Invalid 'value' type for literal_assignment.", line);
                }
                return std::make_unique<LiteralAssignmentStep>(result_index, value);
            }
            else if (type == "execution_assignment")
            {
                std::vector<size_t> result_indices = step_json.at("result").get<std::vector<size_t>>();
                if (result_indices.empty())
                {
                    throw EngineException(EngineErrc::RecipeParseError, "Execution assignment step requires at least one 'result index'.", line);
                }

                std::string function_name = step_json.at("function");
                auto factory_it = m_executable_factory->find(function_name);
                if (factory_it == m_executable_factory->end())
                {
                    throw EngineException(EngineErrc::UnknownFunction, "Unknown function: " + function_name, line);
                }
                auto executable_logic = factory_it->second();
                return std::make_unique<ExecutionAssignmentStep>(
                    result_indices, function_name, line,
                    std::move(executable_logic), step_json.at("args"), *m_executable_factory);
            }
            else if (type == "conditional_assignment")
            {
                size_t result_index = step_json.at("result");
                return std::make_unique<ConditionalAssignmentStep>(
                    result_index, line,
                    step_json.at("condition"), step_json.at("then_expr"), step_json.at("else_expr"),
                    *m_executable_factory);
            }
            else
            {
                throw EngineException(EngineErrc::RecipeParseError, "Unknown execution step type in JSON recipe: " + type, line);
            }
        };

        if (recipe_json.contains("pre_trial_steps"))
        {
            for (const auto &step_json : recipe_json["pre_trial_steps"])
            {
                m_pre_trial_steps.push_back(build_step_from_json(step_json));
            }
        }
        if (recipe_json.contains("per_trial_steps"))
        {
            for (const auto &step_json : recipe_json["per_trial_steps"])
            {
                m_per_trial_steps.push_back(build_step_from_json(step_json));
            }
        }
    }
    catch (const json::out_of_range &e)
    {
        throw EngineException(EngineErrc::RecipeConfigError, "Missing required key in recipe file: " + std::string(e.what()));
    }
    catch (const json::type_error &e)
    {
        throw EngineException(EngineErrc::RecipeConfigError, "Incorrect type for key in recipe file: " + std::string(e.what()));
    }
}

void SimulationEngine::run_pre_trial_phase()
{
    if (!m_is_preview)
    {
        std::cout << "\n--- Running Pre-Trial Phase ---" << std::endl;
    }
    for (const auto &step : m_pre_trial_steps)
    {
        step->execute(m_preloaded_context_vector);
    }
    if (!m_is_preview)
    {
        std::cout << "Pre-trial phase complete. " << m_preloaded_context_vector.size() << " variable slots allocated." << std::endl;
    }
}

void SimulationEngine::run_batch(int num_trials, std::vector<TrialValue> &results, std::exception_ptr &out_exception)
{
    try
    {
        results.reserve(num_trials);
        for (int i = 0; i < num_trials; ++i)
        {
            TrialContext trial_context = m_preloaded_context_vector;
            for (const auto &step : m_per_trial_steps)
            {
                step->execute(trial_context);
            }
            if (m_output_variable_index >= trial_context.size())
            {
                throw EngineException(EngineErrc::IndexOutOfBounds, "Output variable index is out of bounds. This may indicate an incomplete simulation run.");
            }
            results.push_back(trial_context.at(m_output_variable_index));
        }
    }
    catch (...)
    {
        out_exception = std::current_exception();
    }
}

std::vector<TrialValue> SimulationEngine::run()
{
    const unsigned int num_threads = std::max(1u, std::thread::hardware_concurrency());
    const int trials_per_thread = m_num_trials / num_threads;
    const int remainder_trials = m_num_trials % num_threads;

    std::vector<std::thread> threads;
    std::vector<std::vector<TrialValue>> thread_results(num_threads);
    std::vector<std::exception_ptr> thread_exceptions(num_threads, nullptr);

    for (unsigned int i = 0; i < num_threads; ++i)
    {
        int trials_for_this_thread = trials_per_thread + (i == 0 ? remainder_trials : 0);
        if (trials_for_this_thread > 0)
        {
            threads.emplace_back(&SimulationEngine::run_batch, this, trials_for_this_thread, std::ref(thread_results[i]), std::ref(thread_exceptions[i]));
        }
    }
    for (auto &t : threads)
    {
        t.join();
    }
    for (const auto &ex_ptr : thread_exceptions)
    {
        if (ex_ptr)
        {
            std::rethrow_exception(ex_ptr);
        }
    }

    std::vector<TrialValue> final_results;
    final_results.reserve(m_num_trials);
    for (const auto &partial_results : thread_results)
    {
        final_results.insert(final_results.end(), partial_results.begin(), partial_results.end());
    }
    return final_results;
}