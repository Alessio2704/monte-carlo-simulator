#include "engine/SimulationEngine.h"
#include "engine/datastructures.h"

// Include all distribution class headers
#include "distributions/NormalDistribution.h"
#include "distributions/PertDistribution.h"
#include "distributions/UniformDistribution.h"
#include "distributions/LognormalDistribution.h"
#include "distributions/TriangularDistribution.h"
#include "distributions/BernoulliDistribution.h"
#include "distributions/BetaDistribution.h"

// Standard library headers
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

// Use alias for convenience
using json = nlohmann::json;

// --- Mappings and Helpers (as free functions, they don't depend on class state) ---

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
    {"sum_series", OpCode::SUM_SERIES}};

static const std::unordered_map<std::string, DistributionType> STRING_TO_DIST_TYPE_MAP = {
    {"Normal", DistributionType::Normal},
    {"PERT", DistributionType::Pert},
    {"Uniform", DistributionType::Uniform},
    {"Lognormal", DistributionType::Lognormal},
    {"Triangular", DistributionType::Triangular},
    {"Bernoulli", DistributionType::Bernoulli},
    {"Beta", DistributionType::Beta}};

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

// --- SimulationEngine Member Function Implementations ---

SimulationEngine::SimulationEngine(const std::string &json_recipe_path)
    : m_recipe_path(json_recipe_path)
{
    std::cout << "Engine created. Parsing recipe from: " << m_recipe_path << std::endl;
    this->parse_recipe();
}

// CORRECTED: context is now non-const to allow recursive calls to evaluate_operation
TrialValue SimulationEngine::resolve_value(const json &arg, TrialContext &context)
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
    throw std::runtime_error("Invalid argument type in recipe.");
}

// CORRECTED: context is now non-const, matching the header
TrialValue SimulationEngine::evaluate_operation(const Operation &op, TrialContext &context)
{
    switch (op.op_code)
    {
    case OpCode::ADD:
    case OpCode::SUBTRACT:
    case OpCode::MULTIPLY:
    case OpCode::DIVIDE:
    case OpCode::POWER:
    {
        TrialValue arg1 = resolve_value(op.args[0], context);
        TrialValue arg2 = resolve_value(op.args[1], context);

        return std::visit([&](auto &&val1, auto &&val2) -> TrialValue
                          {
                using T1 = std::decay_t<decltype(val1)>;
                using T2 = std::decay_t<decltype(val2)>;

                auto perform_op = [&](double a, double b) -> double {
                    switch(op.op_code) {
                        case OpCode::ADD: return a + b;
                        case OpCode::SUBTRACT: return a - b;
                        case OpCode::MULTIPLY: return a * b;
                        case OpCode::POWER: return std::pow(a, b);
                        case OpCode::DIVIDE: if (b == 0.0) throw std::runtime_error("Division by zero"); return a / b;
                        default: throw std::logic_error("Internal error: Unsupported binary op in visitor.");
                    }
                };

                if constexpr (std::is_same_v<T1, double> && std::is_same_v<T2, double>) {
                    return TrialValue(perform_op(val1, val2));
                } else if constexpr (std::is_same_v<T1, std::vector<double>> && std::is_same_v<T2, double>) {
                    std::vector<double> result; result.reserve(val1.size());
                    for (double x : val1) { result.push_back(perform_op(x, val2)); }
                    return TrialValue(result);
                } else if constexpr (std::is_same_v<T1, double> && std::is_same_v<T2, std::vector<double>>) {
                    std::vector<double> result; result.reserve(val2.size());
                    for (double y : val2) { result.push_back(perform_op(val1, y)); }
                    return TrialValue(result);
                } else if constexpr (std::is_same_v<T1, std::vector<double>> && std::is_same_v<T2, std::vector<double>>) {
                    if (val1.size() != val2.size()) throw std::runtime_error("Vector sizes must match for element-wise operations.");
                    std::vector<double> result; result.reserve(val1.size());
                    for (size_t i = 0; i < val1.size(); ++i) { result.push_back(perform_op(val1[i], val2[i])); }
                    return TrialValue(result);
                } }, arg1, arg2);
    }
    case OpCode::LOG:
        return std::log(std::get<double>(resolve_value(op.args[0], context)));
    case OpCode::LOG10:
        return std::log10(std::get<double>(resolve_value(op.args[0], context)));
    case OpCode::EXP:
        return std::exp(std::get<double>(resolve_value(op.args[0], context)));
    case OpCode::SIN:
        return std::sin(std::get<double>(resolve_value(op.args[0], context)));
    case OpCode::COS:
        return std::cos(std::get<double>(resolve_value(op.args[0], context)));
    case OpCode::TAN:
        return std::tan(std::get<double>(resolve_value(op.args[0], context)));
    case OpCode::GROW_SERIES:
    {
        double base_val = std::get<double>(resolve_value(op.args[0], context));
        double growth_rate = std::get<double>(resolve_value(op.args[1], context));
        int num_years = static_cast<int>(std::get<double>(resolve_value(op.args[2], context)));

        std::vector<double> series;
        series.reserve(num_years);
        double current_val = base_val;
        for (int i = 0; i < num_years; ++i)
        {
            current_val *= (1.0 + growth_rate);
            series.push_back(current_val);
        }
        return series;
    }
    case OpCode::SUM_SERIES:
    {
        const auto series_vec = std::get<std::vector<double>>(resolve_value(op.args[0], context));
        return std::accumulate(series_vec.begin(), series_vec.end(), 0.0);
    }
    case OpCode::NPV:
    {
        double rate = std::get<double>(resolve_value(op.args[0], context));
        const auto cashflows = std::get<std::vector<double>>(resolve_value(op.args[1], context));
        double npv = 0.0;
        for (size_t i = 0; i < cashflows.size(); ++i)
        {
            npv += cashflows[i] / std::pow(1.0 + rate, i + 1);
        }
        return npv;
    }
    default:
        throw std::logic_error("FATAL: Unhandled OpCode in evaluate_operation. This is a programmer error.");
    }
}

void SimulationEngine::run_batch(int num_trials_for_thread, std::vector<double> &thread_results)
{
    thread_results.reserve(num_trials_for_thread);
    for (int i = 0; i < num_trials_for_thread; ++i)
    {
        TrialContext trial_context;
        for (const auto &[name, input_var] : m_recipe.inputs)
        {
            trial_context[name] = (input_var.type == "fixed")
                                      ? TrialValue(input_var.fixed_value)
                                      : TrialValue(m_recipe.distributions.at(name)->getSample());
        }
        for (const auto &op : m_recipe.operations)
        {
            trial_context[op.result_name] = evaluate_operation(op, trial_context);
        }
        thread_results.push_back(std::get<double>(trial_context.at(m_recipe.output_variable)));
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
        // NOTE: This parser is still simplified and assumes fixed inputs are always scalars.
        // A full implementation would need to handle fixed arrays here.
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
        op.op_code = string_to_opcode(op_json["op_code"]);
        op.result_name = op_json["result"];
        op.args = op_json["args"];
        m_recipe.operations.push_back(op);
    }
    std::cout << "Recipe parsing complete." << std::endl;
}