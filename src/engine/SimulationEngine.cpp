#include "engine/SimulationEngine.h"
#include "engine/datastructures.h"

#include "distributions/NormalDistribution.h"
#include "distributions/PertDistribution.h"
#include "distributions/UniformDistribution.h"
#include "distributions/LognormalDistribution.h"
#include "distributions/TriangularDistribution.h"
#include "distributions/BernoulliDistribution.h"
#include "distributions/BetaDistribution.h"

#include <nlohmann/json.hpp>
#include <fstream>
#include <stdexcept>
#include <iostream>
#include <thread>
#include <vector>
#include <cmath>
#include <algorithm>

using json = nlohmann::json;

OpCode string_to_opcode(const std::string &s)
{
    if (s == "multiply")
        return OpCode::MULTIPLY;
    if (s == "add")
        return OpCode::ADD;
    if (s == "subtract")
        return OpCode::SUBTRACT;
    if (s == "divide")
        return OpCode::DIVIDE;
    if (s == "power")
        return OpCode::POWER;
    if (s == "log")
        return OpCode::LOG;
    if (s == "log10")
        return OpCode::LOG10;
    if (s == "exp")
        return OpCode::EXP;
    if (s == "sin")
        return OpCode::SIN;
    if (s == "cos")
        return OpCode::COS;
    if (s == "tan")
        return OpCode::TAN;
    return OpCode::UNKNOWN;
}

DistributionType string_to_dist_type(const std::string &s)
{
    if (s == "Normal")
        return DistributionType::Normal;
    if (s == "PERT")
        return DistributionType::Pert;
    if (s == "Uniform")
        return DistributionType::Uniform;
    if (s == "Lognormal")
        return DistributionType::Lognormal;
    if (s == "Triangular")
        return DistributionType::Triangular;
    if (s == "Bernoulli")
        return DistributionType::Bernoulli;
    if (s == "Beta")
        return DistributionType::Beta;
    return DistributionType::Unknown;
}

SimulationEngine::SimulationEngine(const std::string &json_recipe_path)
    : m_recipe_path(json_recipe_path)
{
    std::cout << "Engine created. Parsing recipe from: " << m_recipe_path << std::endl;
    this->parse_recipe();
}

double SimulationEngine::resolve_value(const json &arg, const std::unordered_map<std::string, double> &context)
{
    if (arg.is_object())
    {
        Operation nested_op;
        nested_op.op_code = string_to_opcode(arg["op_code"]);
        nested_op.args = arg["args"];
        return evaluate_operation(nested_op, context);
    }
    else if (arg.is_string())
    {
        std::string arg_str = arg.get<std::string>();
        auto it = context.find(arg_str);
        if (it != context.end())
        {
            return it->second;
        }
        try
        {
            return std::stod(arg_str);
        }
        catch (const std::exception &)
        {
            throw std::runtime_error("Argument '" + arg_str + "' is not a known variable or a valid number literal.");
        }
    }
    else if (arg.is_number())
    {
        return arg.get<double>();
    }
    throw std::runtime_error("Invalid argument type in recipe.");
}

double SimulationEngine::evaluate_operation(const Operation &op, const std::unordered_map<std::string, double> &context)
{
    switch (op.op_code)
    {
    case OpCode::ADD:
        return resolve_value(op.args[0], context) + resolve_value(op.args[1], context);
    case OpCode::SUBTRACT:
        return resolve_value(op.args[0], context) - resolve_value(op.args[1], context);
    case OpCode::MULTIPLY:
        return resolve_value(op.args[0], context) * resolve_value(op.args[1], context);
    case OpCode::DIVIDE:
    {
        double denominator = resolve_value(op.args[1], context);
        if (denominator == 0)
            throw std::runtime_error("Division by zero.");
        return resolve_value(op.args[0], context) / denominator;
    }
    case OpCode::POWER:
        return std::pow(resolve_value(op.args[0], context), resolve_value(op.args[1], context));
    case OpCode::LOG:
        return std::log(resolve_value(op.args[0], context));
    case OpCode::LOG10:
        return std::log10(resolve_value(op.args[0], context));
    case OpCode::EXP:
        return std::exp(resolve_value(op.args[0], context));
    case OpCode::SIN:
        return std::sin(resolve_value(op.args[0], context));
    case OpCode::COS:
        return std::cos(resolve_value(op.args[0], context));
    case OpCode::TAN:
        return std::tan(resolve_value(op.args[0], context));
    default:
        throw std::runtime_error("Unsupported or unknown op_code during evaluation.");
    }
}

void SimulationEngine::run_batch(int num_trials_for_thread, std::vector<double> &thread_results)
{
    thread_results.reserve(num_trials_for_thread);

    for (int i = 0; i < num_trials_for_thread; ++i)
    {
        std::unordered_map<std::string, double> trial_context;

        for (const auto &[name, input_var] : m_recipe.inputs)
        {
            trial_context[name] = (input_var.type == "fixed")
                                      ? input_var.fixed_value
                                      : m_recipe.distributions.at(name)->getSample();
        }

        for (const auto &op : m_recipe.operations)
        {
            trial_context[op.result_name] = evaluate_operation(op, trial_context);
        }

        thread_results.push_back(trial_context.at(m_recipe.output_variable));
    }
}

std::vector<double> SimulationEngine::run()
{
    std::cout << "Starting simulation..." << std::endl;

    const unsigned int num_threads = std::max(1u, std::thread::hardware_concurrency());
    std::cout << "Using " << num_threads << " threads for simulation." << std::endl;

    const int trials_per_thread = m_recipe.num_trials / num_threads;
    const int remainder_trials = m_recipe.num_trials % num_threads;

    std::vector<std::thread> threads;
    std::vector<std::vector<double>> thread_results(num_threads);

    for (unsigned int i = 0; i < num_threads; ++i)
    {
        int trials_for_this_thread = trials_per_thread;
        if (i == 0)
        {
            trials_for_this_thread += remainder_trials;
        }

        if (trials_for_this_thread > 0)
        {
            threads.emplace_back(&SimulationEngine::run_batch, this, trials_for_this_thread, std::ref(thread_results[i]));
        }
    }

    for (auto &t : threads)
    {
        t.join();
    }

    std::vector<double> final_results;
    final_results.reserve(m_recipe.num_trials);
    for (const auto &partial_results : thread_results)
    {
        final_results.insert(final_results.end(), partial_results.begin(), partial_results.end());
    }

    std::cout << "Simulation run complete. " << final_results.size() << " trials executed." << std::endl;
    return final_results;
}

void SimulationEngine::create_distribution_from_input(const std::string &name, const InputVariable &var)
{
    DistributionType dist_type = string_to_dist_type(var.dist_name);
    switch (dist_type)
    {
    case DistributionType::Normal:
        m_recipe.distributions[name] = std::make_unique<NormalDistribution>(
            var.dist_params.at("mean"), var.dist_params.at("stddev"));
        break;
    case DistributionType::Pert:
        m_recipe.distributions[name] = std::make_unique<PertDistribution>(
            var.dist_params.at("min"), var.dist_params.at("mostLikely"), var.dist_params.at("max"));
        break;
    case DistributionType::Uniform:
        m_recipe.distributions[name] = std::make_unique<UniformDistribution>(
            var.dist_params.at("min"), var.dist_params.at("max"));
        break;
    case DistributionType::Lognormal:
        m_recipe.distributions[name] = std::make_unique<LognormalDistribution>(
            var.dist_params.at("log_mean"), var.dist_params.at("log_stddev"));
        break;
    case DistributionType::Triangular:
        m_recipe.distributions[name] = std::make_unique<TriangularDistribution>(
            var.dist_params.at("min"), var.dist_params.at("mostLikely"), var.dist_params.at("max"));
        break;
    case DistributionType::Bernoulli:
        m_recipe.distributions[name] = std::make_unique<BernoulliDistribution>(
            var.dist_params.at("p"));
        break;
    case DistributionType::Beta:
        m_recipe.distributions[name] = std::make_unique<BetaDistribution>(
            var.dist_params.at("alpha"), var.dist_params.at("beta"));
        break;
    case DistributionType::Unknown:
    default:
        throw std::runtime_error("Unknown distribution type in recipe: " + var.dist_name);
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
            var.fixed_value = input_json["value"];
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

        m_recipe.inputs[name] = var;
    }

    for (const auto &op_json : recipe_json["operations"])
    {
        Operation op;
        std::string op_code_str = op_json["op_code"];
        op.op_code = string_to_opcode(op_code_str);

        op.result_name = op_json["result"];
        op.args = op_json["args"];
        m_recipe.operations.push_back(op);
    }

    std::cout << "Recipe parsing complete." << std::endl;
}