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

using json = nlohmann::json;

// Helper function to convert string to OpCode
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

// Helper function to convert string to DistributionType, now with all types
DistributionType string_to_dist_type(const std::string &s)
{
    if (s == "Normal")
        return DistributionType::Normal;
    if (s == "Pert")
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

// Constructor (remains the same)
SimulationEngine::SimulationEngine(const std::string &json_recipe_path)
    : m_recipe_path(json_recipe_path)
{
    std::cout << "Engine created. Parsing recipe from: " << m_recipe_path << std::endl;
    this->parse_recipe();
}

// run() method (remains the same)
std::vector<double> SimulationEngine::run()
{
    std::cout << "Starting simulation..." << std::endl;
    std::vector<double> final_results;
    final_results.reserve(m_recipe.num_trials);

    for (int i = 0; i < m_recipe.num_trials; ++i)
    {
        std::unordered_map<std::string, double> trial_context;

        for (const auto &[name, input_var] : m_recipe.inputs)
        {
            if (input_var.type == "fixed")
            {
                trial_context[name] = input_var.fixed_value;
            }
            else if (input_var.type == "distribution")
            {
                trial_context[name] = m_recipe.distributions.at(name)->getSample();
            }
        }

        for (const auto &op : m_recipe.operations)
        {
            switch (op.op_code)
            {
            case OpCode::MULTIPLY:
            {
                double val1 = trial_context.at(op.args[0]);
                double val2 = trial_context.at(op.args[1]);
                trial_context[op.result_name] = val1 * val2;
                break;
            }
            case OpCode::ADD:
            {
                double val1 = trial_context.at(op.args[0]);
                double val2 = trial_context.at(op.args[1]);
                trial_context[op.result_name] = val1 + val2;
                break;
            }
            case OpCode::SUBTRACT:
            {
                double val1 = trial_context.at(op.args[0]);
                double val2 = trial_context.at(op.args[1]);
                trial_context[op.result_name] = val1 - val2;
                break;
            }
            case OpCode::DIVIDE:
            {
                double val1 = trial_context.at(op.args[0]);
                double val2 = trial_context.at(op.args[1]);
                if (val2 == 0)
                {
                    throw std::runtime_error("Division by zero in op: " + op.result_name);
                }
                trial_context[op.result_name] = val1 / val2;
                break;
            }
            case OpCode::POWER:
            {
                double base = trial_context.at(op.args[0]);
                double exponent = trial_context.at(op.args[1]);
                trial_context[op.result_name] = std::pow(base, exponent);
                break;
            }
            case OpCode::LOG:
            {
                double val = trial_context.at(op.args[0]);
                trial_context[op.result_name] = std::log(val);
                break;
            }
            case OpCode::LOG10:
            {
                double val = trial_context.at(op.args[0]);
                trial_context[op.result_name] = std::log10(val);
                break;
            }
            case OpCode::EXP:
            {
                double val = trial_context.at(op.args[0]);
                trial_context[op.result_name] = std::exp(val);
                break;
            }
            case OpCode::SIN:
            {
                double val = trial_context.at(op.args[0]);
                trial_context[op.result_name] = std::sin(val);
                break;
            }
            case OpCode::COS:
            {
                double val = trial_context.at(op.args[0]);
                trial_context[op.result_name] = std::cos(val);
                break;
            }
            case OpCode::TAN:
            {
                double val = trial_context.at(op.args[0]);
                trial_context[op.result_name] = std::tan(val);
                break;
            }
            case OpCode::UNKNOWN:
                throw std::runtime_error("Encountered an unknown or unsupported op_code during simulation.");
            }
        }
        final_results.push_back(trial_context.at(m_recipe.output_variable));
    }

    std::cout << "Simulation run complete. " << m_recipe.num_trials << " trials executed." << std::endl;
    return final_results;
}

// The private parser method with the fully expanded Distribution Factory switch
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
        m_recipe.inputs[name] = var;
    }

    for (const auto &op_json : recipe_json["operations"])
    {
        Operation op;
        std::string op_code_str = op_json["op_code"];
        op.op_code = string_to_opcode(op_code_str);

        op.result_name = op_json["result"];
        op.args = op_json["args"].get<std::vector<std::string>>();
        m_recipe.operations.push_back(op);
    }

    std::cout << "Recipe parsing complete." << std::endl;
}