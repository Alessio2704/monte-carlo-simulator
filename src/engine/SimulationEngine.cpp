#include "engine/SimulationEngine.h"
#include "engine/datastructures.h"

#include "distributions/NormalDistribution.h"
#include "distributions/PertDistribution.h"
#include "distributions/UniformDistribution.h"
#include "distributions/LognormalDistribution.h"
#include "distributions/TriangularDistribution.h"
#include "distributions/BernoulliDistribution.h"
#include "distributions/BetaDistribution.h"

#include "engine/operations.h"

#include <nlohmann/json.hpp>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <thread>
#include <vector>
#include <cmath>
#include <algorithm>
#include <unordered_map>
#include <variant>
#include <numeric>

using json = nlohmann::json;

static const std::unordered_map<std::string, OpCode> STRING_TO_OPCODE_MAP = {
    {"add", OpCode::ADD},
    {"subtract", OpCode::SUBTRACT},
    {"multiply", OpCode::MULTIPLY},
    {"divide", OpCode::DIVIDE},
    {"power", OpCode::POWER},
    {"log", OpCode::LOG},
    {"log10", OpCode::LOG10},
    {"exp", OpCode::EXP},
    {"sin", OpCode::SIN},
    {"cos", OpCode::COS},
    {"tan", OpCode::TAN},
    {"grow_series", OpCode::GROW_SERIES},
    {"npv", OpCode::NPV},
    {"sum_series", OpCode::SUM_SERIES},
    {"get_element", OpCode::GET_ELEMENT},
    {"series_delta", OpCode::SERIES_DELTA},
    {"compound_series", OpCode::COMPOUND_SERIES},
    {"compose_vector", OpCode::COMPOSE_VECTOR}};

static const std::unordered_map<std::string, DistributionType>
    STRING_TO_DIST_TYPE_MAP = {{"Normal", DistributionType::Normal}, {"PERT", DistributionType::Pert}, {"Uniform", DistributionType::Uniform}, {"Lognormal", DistributionType::Lognormal}, {"Triangular", DistributionType::Triangular}, {"Bernoulli", DistributionType::Bernoulli}, {"Beta", DistributionType::Beta}};

OpCode string_to_opcode(const std::string &s)
{
    auto it = STRING_TO_OPCODE_MAP.find(s);
    if (it != STRING_TO_OPCODE_MAP.end())
    {
        return it->second;
    }
    throw std::runtime_error("Invalid op_code string in recipe: " + s);
}

DistributionType string_to_dist_type(const std::string &s)
{
    auto it = STRING_TO_DIST_TYPE_MAP.find(s);
    if (it != STRING_TO_DIST_TYPE_MAP.end())
    {
        return it->second;
    }
    throw std::runtime_error("Invalid dist_name string in recipe: " + s);
}

SimulationEngine::SimulationEngine(const std::string &json_recipe_path)
    : m_recipe_path(json_recipe_path)
{

    // --- Build the Operation Factory ---
    // For each OpCode, create an instance of its corresponding strategy class.
    m_operations[OpCode::ADD] = std::make_unique<AddOperation>();
    m_operations[OpCode::SUBTRACT] = std::make_unique<SubtractOperation>();
    m_operations[OpCode::MULTIPLY] = std::make_unique<MultiplyOperation>();
    m_operations[OpCode::DIVIDE] = std::make_unique<DivideOperation>();
    m_operations[OpCode::POWER] = std::make_unique<PowerOperation>();
    m_operations[OpCode::LOG] = std::make_unique<LogOperation>();
    m_operations[OpCode::LOG10] = std::make_unique<Log10Operation>();
    m_operations[OpCode::EXP] = std::make_unique<ExpOperation>();
    m_operations[OpCode::SIN] = std::make_unique<SinOperation>();
    m_operations[OpCode::COS] = std::make_unique<CosOperation>();
    m_operations[OpCode::TAN] = std::make_unique<TanOperation>();
    m_operations[OpCode::GROW_SERIES] = std::make_unique<GrowSeriesOperation>();
    m_operations[OpCode::COMPOUND_SERIES] = std::make_unique<CompoundSeriesOperation>();
    m_operations[OpCode::NPV] = std::make_unique<NpvOperation>();
    m_operations[OpCode::SUM_SERIES] = std::make_unique<SumSeriesOperation>();
    m_operations[OpCode::GET_ELEMENT] = std::make_unique<GetElementOperation>();
    m_operations[OpCode::SERIES_DELTA] = std::make_unique<SeriesDeltaOperation>();
    m_operations[OpCode::COMPOSE_VECTOR] = std::make_unique<ComposeVectorOperation>();

    std::cout << "Engine created and operation factory built. Parsing recipe from: " << m_recipe_path << std::endl;
    this->parse_recipe();
}

void SimulationEngine::create_distribution_from_input(const std::string &name, const InputVariable &var)
{
    DistributionType dist_type = string_to_dist_type(var.dist_name);
    switch (dist_type)
    {
    case DistributionType::Normal:
        m_recipe.distributions[name] = std::make_unique<NormalDistribution>(var.dist_params.at("mean"), var.dist_params.at("stddev"));
        break;
    case DistributionType::Pert:
        m_recipe.distributions[name] = std::make_unique<PertDistribution>(var.dist_params.at("min"), var.dist_params.at("mostLikely"), var.dist_params.at("max"));
        break;
    case DistributionType::Uniform:
        m_recipe.distributions[name] = std::make_unique<UniformDistribution>(var.dist_params.at("min"), var.dist_params.at("max"));
        break;
    case DistributionType::Lognormal:
        m_recipe.distributions[name] = std::make_unique<LognormalDistribution>(var.dist_params.at("log_mean"), var.dist_params.at("log_stddev"));
        break;
    case DistributionType::Triangular:
        m_recipe.distributions[name] = std::make_unique<TriangularDistribution>(var.dist_params.at("min"), var.dist_params.at("mostLikely"), var.dist_params.at("max"));
        break;
    case DistributionType::Bernoulli:
        m_recipe.distributions[name] = std::make_unique<BernoulliDistribution>(var.dist_params.at("p"));
        break;
    case DistributionType::Beta:
        m_recipe.distributions[name] = std::make_unique<BetaDistribution>(var.dist_params.at("alpha"), var.dist_params.at("beta"));
        break;
    }
}

void SimulationEngine::parse_recipe()
{
    std::ifstream file_stream(m_recipe_path);

    if (!file_stream.is_open())
    {
        throw std::runtime_error("Failed to open recipe file: " + m_recipe_path);
    }

    json recipe_json = json::parse(file_stream);
    m_recipe.num_trials = recipe_json["simulation_config"]["num_trials"];
    m_recipe.output_variable = recipe_json["output_variable"];

    for (const auto &[name, input_json] : recipe_json["inputs"].items())
    {
        InputVariable var;
        var.type = input_json["type"];

        if (var.type == "fixed")
        {
            if (input_json["value"].is_array())
            {
                var.value = input_json["value"].get<std::vector<double>>();
            }
            else if (input_json["value"].is_number())
            {
                var.value = input_json["value"].get<double>();
            }
            else
            {
                throw std::runtime_error("Fixed input '" + name + "' has an invalid 'value' type. Must be number or array.");
            }
        }
        else if (var.type == "distribution")
        {
            var.dist_name = input_json["dist_name"];
            for (const auto &[param_name, param_value] : input_json["params"].items())
            {
                var.dist_params[param_name] = param_value;
            }
            create_distribution_from_input(name, var);
        }
        else
        {
            throw std::runtime_error("Input '" + name + "' has an unknown type: " + var.type);
        }
        m_recipe.inputs[name] = var;
    }

    for (const auto &op_json : recipe_json["operations"])
    {
        Operation op;
        op.op_code = string_to_opcode(op_json["op_code"]);
        op.result_name = op_json["result"];
        op.args = op_json["args"];
        m_recipe.operations.push_back(op);
    }
    std::cout << "Recipe parsing complete." << std::endl;
}

TrialValue SimulationEngine::resolve_value(const json &arg, TrialContext &context)
{
    if (arg.is_string())
    {
        std::string arg_str = arg.get<std::string>();
        auto it = context.find(arg_str);
        if (it != context.end())
        {
            return it->second;
        }
        try
        {
            return TrialValue(std::stod(arg_str));
        }
        catch (const std::exception &)
        {
            throw std::runtime_error("Argument '" + arg_str + "' is not a known variable or a valid number literal.");
        }
    }
    else if (arg.is_number())
    {
        return TrialValue(arg.get<double>());
    }
    else if (arg.is_array())
    {
        return TrialValue(arg.get<std::vector<double>>());
    }
    // This function no longer handles objects. If it receives one, it's an error in the calling logic.
    throw std::runtime_error("Invalid argument type passed to resolve_value. Expected string, number, or array.");
}

void SimulationEngine::run_batch(int num_trials_for_thread, std::vector<TrialValue> &thread_results, std::exception_ptr &out_exception)
{
    try
    {
        thread_results.reserve(num_trials_for_thread);
        for (int i = 0; i < num_trials_for_thread; ++i)
        {
            TrialContext trial_context;
            for (const auto &[name, input_var] : m_recipe.inputs)
            {
                trial_context[name] = (input_var.type == "fixed")
                                          ? input_var.value
                                          : TrialValue(m_recipe.distributions.at(name)->getSample());
            }

            // The recursive lambda for resolving arguments, including nested expressions.
            std::function<TrialValue(const json &)> resolve_recursive;
            resolve_recursive =
                [&](const json &arg_json) -> TrialValue
            {
                if (arg_json.is_object())
                {
                    Operation nested_op;
                    nested_op.op_code = string_to_opcode(arg_json["op_code"]);
                    nested_op.args = arg_json["args"];

                    auto it = m_operations.find(nested_op.op_code);
                    if (it == m_operations.end())
                        throw std::logic_error("FATAL: Unhandled nested OpCode.");

                    std::vector<TrialValue> nested_resolved_args;
                    for (const auto &nested_arg_json : nested_op.args)
                    {
                        nested_resolved_args.push_back(resolve_recursive(nested_arg_json));
                    }
                    return it->second->execute(nested_resolved_args);
                }
                else
                {
                    return resolve_value(arg_json, trial_context);
                }
            };

            for (const auto &op : m_recipe.operations)
            {
                std::vector<TrialValue> resolved_args;
                resolved_args.reserve(op.args.size());
                for (const auto &arg_json : op.args)
                {
                    resolved_args.push_back(resolve_recursive(arg_json));
                }

                auto it = m_operations.find(op.op_code);
                if (it == m_operations.end())
                {
                    throw std::logic_error("FATAL: Unhandled OpCode. This is a programmer error.");
                }

                trial_context[op.result_name] = it->second->execute(resolved_args);
            }

            // --- THE FIX ---
            // We no longer assert the type here. We push the entire TrialValue (scalar OR vector)
            // into the results. The 'print_statistics' function will handle the type check.
            thread_results.push_back(trial_context.at(m_recipe.output_variable));
        }
    }
    catch (...)
    {
        out_exception = std::current_exception();
    }
}

std::vector<TrialValue> SimulationEngine::run()
{
    std::cout << "Starting simulation..." << std::endl;
    const unsigned int num_threads = std::max(1u, std::thread::hardware_concurrency());
    std::cout << "Using " << num_threads << " threads for simulation." << std::endl;
    const int trials_per_thread = m_recipe.num_trials / num_threads;
    const int remainder_trials = m_recipe.num_trials % num_threads;

    std::vector<std::thread> threads;
    // The per-thread results vector is now a vector of TrialValue
    std::vector<std::vector<TrialValue>> thread_results(num_threads);
    std::vector<std::exception_ptr> thread_exceptions(num_threads, nullptr);

    for (unsigned int i = 0; i < num_threads; ++i)
    {
        int trials_for_this_thread = trials_per_thread;
        if (i == 0)
        {
            trials_for_this_thread += remainder_trials;
        }
        if (trials_for_this_thread > 0)
        {
            threads.emplace_back(&SimulationEngine::run_batch, this, trials_for_this_thread,
                                 std::ref(thread_results[i]), std::ref(thread_exceptions[i]));
        }
    }

    for (auto &t : threads)
    {
        t.join();
    }

    for (const auto &ex_ptr : thread_exceptions)
    {
        if (ex_ptr != nullptr)
        {
            std::rethrow_exception(ex_ptr);
        }
    }

    // The final results vector is now a vector of TrialValue
    std::vector<TrialValue> final_results;
    final_results.reserve(m_recipe.num_trials);
    for (const auto &partial_results : thread_results)
    {
        final_results.insert(final_results.end(), partial_results.begin(), partial_results.end());
    }
    std::cout << "Simulation run complete. " << final_results.size() << " trials executed." << std::endl;
    return final_results;
}