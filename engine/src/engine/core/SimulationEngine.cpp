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

SimulationEngine::SimulationEngine(const std::string &json_recipe_path)
{
    build_executable_factory();
    parse_recipe(json_recipe_path);
    run_pre_trial_phase();
    build_per_trial_steps();
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

    m_executable_factory["series_delta"] = []
    { return std::make_unique<SeriesDeltaOperation>(); };

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
    return m_recipe.output_file_path;
}

void SimulationEngine::parse_recipe(const std::string &path)
{
    std::ifstream file_stream(path);
    if (!file_stream.is_open())
    {
        throw std::runtime_error("Failed to open recipe file: " + path);
    }
    json recipe_json = json::parse(file_stream);

    const auto &config = recipe_json["simulation_config"];

    m_recipe.num_trials = config["num_trials"];
    m_recipe.output_variable = recipe_json["output_variable"];

    if (config.contains("output_file"))
    {
        if (config["output_file"].is_string())
        {
            m_recipe.output_file_path = config["output_file"].get<std::string>();
        }
    }

    // Helper lambda to parse a step_def from json
    auto parse_step = [](const json &step_json) -> ExecutionStepDef
    {
        std::string type = step_json["type"];
        if (type == "literal_assignment")
        {
            LiteralAssignmentDef def;
            def.result_name = step_json["result"];
            const auto &val = step_json["value"];
            if (val.is_array())
            {
                def.value = val.get<std::vector<double>>();
            }
            else if (val.is_number())
            {
                def.value = val.get<double>();
            }
            else
            {
                throw std::runtime_error("Invalid 'value' type for literal_assignment.");
            }
            return def;
        }
        else if (type == "execution_assignment")
        {
            ExecutionAssignmentDef def;
            def.result_name = step_json["result"];
            def.function_name = step_json["function"];
            def.args = step_json["args"];
            return def;
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
            m_recipe.pre_trial_steps.push_back(parse_step(step_json));
        }
    }

    if (recipe_json.contains("per_trial_steps"))
    {
        for (const auto &step_json : recipe_json["per_trial_steps"])
        {
            m_recipe.per_trial_steps.push_back(parse_step(step_json));
        }
    }
}

void SimulationEngine::run_pre_trial_phase()
{
    std::cout << "\n--- Running Pre-Trial Phase ---" << std::endl;
    // This method builds and executes pre-trial steps immediately.
    for (const auto &step_def_variant : m_recipe.pre_trial_steps)
    {
        std::visit([this](auto &&step_def)
                   {
            using T = std::decay_t<decltype(step_def)>;
            std::unique_ptr<IExecutionStep> step_to_execute;

            if constexpr (std::is_same_v<T, LiteralAssignmentDef>) {
                step_to_execute = std::make_unique<LiteralAssignmentStep>(step_def.result_name, step_def.value);
            } else if constexpr (std::is_same_v<T, ExecutionAssignmentDef>) {
                auto it = m_executable_factory.find(step_def.function_name);
                if (it == m_executable_factory.end()) {
                    throw std::runtime_error("Unknown function in pre-trial recipe: " + step_def.function_name);
                }
                auto executable_logic = it->second();
                step_to_execute = std::make_unique<ExecutionAssignmentStep>(
                    step_def.result_name, std::move(executable_logic), step_def.args, m_executable_factory
                );
            }
            // Execute the step and store the result in the preloaded context.
            step_to_execute->execute(m_preloaded_context); },
                   step_def_variant);
    }
    std::cout << "Pre-trial phase complete. " << m_preloaded_context.size() << " variable(s) loaded." << std::endl;
}

void SimulationEngine::build_per_trial_steps()
{
    for (const auto &step_def_variant : m_recipe.per_trial_steps)
    {
        std::visit([this](auto &&step_def)
                   {
            using T = std::decay_t<decltype(step_def)>;

            if constexpr (std::is_same_v<T, LiteralAssignmentDef>) {
                m_per_trial_steps.push_back(
                    std::make_unique<LiteralAssignmentStep>(step_def.result_name, step_def.value)
                );
            } else if constexpr (std::is_same_v<T, ExecutionAssignmentDef>) {
                auto it = m_executable_factory.find(step_def.function_name);
                if (it == m_executable_factory.end()) {
                    throw std::runtime_error("Unknown function in recipe: " + step_def.function_name);
                }
                
                auto executable_logic = it->second(); 
                
                m_per_trial_steps.push_back(
                    std::make_unique<ExecutionAssignmentStep>(
                        step_def.result_name,
                        std::move(executable_logic),
                        step_def.args,
                        m_executable_factory
                    )
                );
            } }, step_def_variant);
    }
}

void SimulationEngine::run_batch(int num_trials, std::vector<TrialValue> &results, std::exception_ptr &out_exception)
{
    try
    {
        results.reserve(num_trials);
        for (int i = 0; i < num_trials; ++i)
        {
            // Each trial starts with a copy of the pre-loaded context.
            TrialContext trial_context = m_preloaded_context;

            for (const auto &step : m_per_trial_steps)
            {
                step->execute(trial_context);
            }
            // Ensure the output variable exists before trying to access it
            if (trial_context.count(m_recipe.output_variable))
            {
                results.push_back(trial_context.at(m_recipe.output_variable));
            }
            else
            {
                throw std::runtime_error("Output variable '" + m_recipe.output_variable + "' was not calculated in the simulation.");
            }
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
    const int trials_per_thread = m_recipe.num_trials / num_threads;
    const int remainder_trials = m_recipe.num_trials % num_threads;

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
    final_results.reserve(m_recipe.num_trials);
    for (const auto &partial_results : thread_results)
    {
        final_results.insert(final_results.end(), partial_results.begin(), partial_results.end());
    }
    return final_results;
}