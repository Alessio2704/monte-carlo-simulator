#include "include/engine/core/SimulationEngine.h"
#include "include/engine/functions/operations.h"
#include "include/engine/functions/samplers.h"
#include "include/engine/core/ExecutionSteps.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <thread>
#include <vector>

using json = nlohmann::json;

SimulationEngine::SimulationEngine(const std::string &json_recipe_path, bool is_preview)
    : m_is_preview(is_preview)
{
    build_executable_factory();
    parse_and_build(json_recipe_path);
    run_pre_trial_phase();
}

void SimulationEngine::build_executable_factory()
{
    // It stores functions (lambdas) that create the objects.

    // Operations
    m_executable_factory["add"] = []
    { return std::make_unique<AddOperation>(); };
    m_executable_factory["subtract"] = []
    { return std::make_unique<SubtractOperation>(); };
    m_executable_factory["multiply"] = []
    { return std::make_unique<MultiplyOperation>(); };
    m_executable_factory["divide"] = []
    { return std::make_unique<DivideOperation>(); };
    m_executable_factory["power"] = []
    { return std::make_unique<PowerOperation>(); };
    m_executable_factory["log"] = []
    { return std::make_unique<LogOperation>(); };
    m_executable_factory["log10"] = []
    { return std::make_unique<Log10Operation>(); };
    m_executable_factory["exp"] = []
    { return std::make_unique<ExpOperation>(); };
    m_executable_factory["sin"] = []
    { return std::make_unique<SinOperation>(); };
    m_executable_factory["cos"] = []
    { return std::make_unique<CosOperation>(); };
    m_executable_factory["tan"] = []
    { return std::make_unique<TanOperation>(); };
    m_executable_factory["identity"] = []
    { return std::make_unique<IdentityOperation>(); };
    m_executable_factory["grow_series"] = []
    { return std::make_unique<GrowSeriesOperation>(); };
    m_executable_factory["compound_series"] = []
    { return std::make_unique<CompoundSeriesOperation>(); };
    m_executable_factory["npv"] = []
    { return std::make_unique<NpvOperation>(); };
    m_executable_factory["sum_series"] = []
    { return std::make_unique<SumSeriesOperation>(); };
    m_executable_factory["get_element"] = []
    { return std::make_unique<GetElementOperation>(); };
    m_executable_factory["delete_element"] = []
    { return std::make_unique<DeleteElementOperation>(); };
    m_executable_factory["series_delta"] = []
    { return std::make_unique<SeriesDeltaOperation>(); };
    m_executable_factory["compose_vector"] = []
    { return std::make_unique<ComposeVectorOperation>(); };
    m_executable_factory["interpolate_series"] = []
    { return std::make_unique<InterpolateSeriesOperation>(); };
    m_executable_factory["capitalize_expense"] = []
    { return std::make_unique<CapitalizeExpenseOperation>(); };

    m_executable_factory["read_csv_scalar"] = []
    { return std::make_unique<ReadCsvScalarOperation>(); };
    m_executable_factory["read_csv_vector"] = []
    { return std::make_unique<ReadCsvVectorOperation>(); };

    // Distribution Samplers
    m_executable_factory["Normal"] = []
    { return std::make_unique<NormalSampler>(); };
    m_executable_factory["Uniform"] = []
    { return std::make_unique<UniformSampler>(); };
    m_executable_factory["Bernoulli"] = []
    { return std::make_unique<BernoulliSampler>(); };
    m_executable_factory["Lognormal"] = []
    { return std::make_unique<LognormalSampler>(); };
    m_executable_factory["Beta"] = []
    { return std::make_unique<BetaSampler>(); };
    m_executable_factory["Pert"] = []
    { return std::make_unique<PertSampler>(); };
    m_executable_factory["Triangular"] = []
    { return std::make_unique<TriangularSampler>(); };
}

std::string SimulationEngine::get_output_file_path() const
{
    return m_output_file_path;
}

void SimulationEngine::parse_and_build(const std::string &path)
{
    // --- 1. Read JSON and load config ---
    std::ifstream file_stream(path);
    if (!file_stream.is_open())
    {
        throw std::runtime_error("Failed to open recipe file: " + path);
    }
    json recipe_json = json::parse(file_stream);
    const auto &config = recipe_json["simulation_config"];
    m_num_trials = config["num_trials"];
    m_output_variable = recipe_json["output_variable"];
    if (config.contains("output_file") && config["output_file"].is_string())
    {
        m_output_file_path = config["output_file"].get<std::string>();
    }

    // --- 2. Build Variable Registry by pre-scanning all steps ---
    size_t current_index = 0;
    auto register_variable_if_new = [&](const std::string &name)
    {
        if (m_variable_registry.find(name) == m_variable_registry.end())
        {
            m_variable_registry[name] = current_index++;
        }
    };

    if (recipe_json.contains("pre_trial_steps"))
    {
        for (const auto &step_json : recipe_json["pre_trial_steps"])
        {
            register_variable_if_new(step_json["result"].get<std::string>());
        }
    }
    if (recipe_json.contains("per_trial_steps"))
    {
        for (const auto &step_json : recipe_json["per_trial_steps"])
        {
            register_variable_if_new(step_json["result"].get<std::string>());
        }
    }

    // Find the index for the final output variable and pre-allocate context vector
    auto it = m_variable_registry.find(m_output_variable);
    if (it == m_variable_registry.end())
    {
        throw std::runtime_error("Output variable '" + m_output_variable + "' is not defined in any step.");
    }
    m_output_variable_index = it->second;
    m_preloaded_context_vector.resize(m_variable_registry.size());

    // --- 3. Build Executable Step objects directly from JSON ---
    auto build_step_from_json = [&](const json &step_json) -> std::unique_ptr<IExecutionStep>
    {
        std::string type = step_json["type"];
        std::string result_name = step_json["result"];
        int line = step_json.value("line", -1);
        size_t result_index = m_variable_registry.at(result_name);

        if (type == "literal_assignment")
        {
            const auto &val_json = step_json["value"];
            TrialValue value;
            if (val_json.is_array())
            {
                value = val_json.get<std::vector<double>>();
            }
            else if (val_json.is_number())
            {
                value = val_json.get<double>();
            }
            else
            {
                throw std::runtime_error("Invalid 'value' type for literal_assignment.");
            }
            return std::make_unique<LiteralAssignmentStep>(result_index, value);
        }
        else if (type == "execution_assignment")
        {
            std::string function_name = step_json["function"];
            auto factory_it = m_executable_factory.find(function_name);
            if (factory_it == m_executable_factory.end())
            {
                throw std::runtime_error("Unknown function: " + function_name);
            }
            auto executable_logic = factory_it->second();
            return std::make_unique<ExecutionAssignmentStep>(
                result_index, function_name, line,
                std::move(executable_logic), step_json["args"], m_executable_factory, m_variable_registry);
        }
        else
        {
            throw std::runtime_error("Unknown execution step type in JSON recipe: " + type);
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