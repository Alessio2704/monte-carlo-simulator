#include "engine/SimulationEngine.h"
#include "engine/datastructures.h"
// Include all our distribution class headers
#include "distributions/NormalDistribution.h"
#include "distributions/PertDistribution.h"
#include "distributions/UniformDistribution.h"
#include "distributions/LognormalDistribution.h"
#include "distributions/TriangularDistribution.h"
#include "distributions/BernoulliDistribution.h"
#include "distributions/BetaDistribution.h"

// The header for the nlohmann/json library
#include <nlohmann/json.hpp>

#include <fstream>
#include <stdexcept>
#include <iostream>
#include <cmath> // Required for std::pow, std::log, etc.

// Use the 'json' alias for convenience
using json = nlohmann::json;

// --- Helper function implementations ---

// Converts a string from the recipe to its corresponding OpCode enum
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

// Converts a string from the recipe to its corresponding DistributionType enum
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

// --- SimulationEngine Method Implementations ---

// Constructor: Stores the path and immediately calls the parser.
SimulationEngine::SimulationEngine(const std::string &json_recipe_path)
    : m_recipe_path(json_recipe_path)
{
    std::cout << "Engine created. Parsing recipe from: " << m_recipe_path << std::endl;
    this->parse_recipe();
}

// The main public method to run the simulation loop.
std::vector<double> SimulationEngine::run()
{
    std::cout << "Starting simulation..." << std::endl;
    std::vector<double> final_results;
    final_results.reserve(m_recipe.num_trials);

    for (int i = 0; i < m_recipe.num_trials; ++i)
    {
        // This map is the "scratchpad" for the current trial's calculations.
        std::unordered_map<std::string, double> trial_context;

        // Populate the context with initial values for this trial (sampling from distributions).
        for (const auto &[name, input_var] : m_recipe.inputs)
        {
            trial_context[name] = (input_var.type == "fixed")
                                      ? input_var.fixed_value
                                      : m_recipe.distributions.at(name)->getSample();
        }

        // Execute the main operations list, storing results back into the context.
        for (const auto &op : m_recipe.operations)
        {
            trial_context[op.result_name] = evaluate_operation(op, trial_context);
        }

        // After all operations are done, store the designated final output value.
        final_results.push_back(trial_context.at(m_recipe.output_variable));
    }

    std::cout << "Simulation run complete. " << m_recipe.num_trials << " trials executed." << std::endl;
    return final_results;
}

// --- Private Helper Methods for Execution ---

// Recursively resolves any JSON argument (variable, literal, or nested operation) into a double.
double SimulationEngine::resolve_value(const json &arg, const std::unordered_map<std::string, double> &context)
{
    if (arg.is_object())
    {
        Operation nested_op;
        nested_op.op_code = string_to_opcode(arg.at("op_code"));
        nested_op.args = arg.at("args");
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

// Executes a single operation by dispatching to the correct logic based on its OpCode.
double SimulationEngine::evaluate_operation(const Operation &op, const std::unordered_map<std::string, double> &context)
{
    switch (op.op_code)
    {
    case OpCode::ADD:
        return resolve_value(op.args.at(0), context) + resolve_value(op.args.at(1), context);
    case OpCode::SUBTRACT:
        return resolve_value(op.args.at(0), context) - resolve_value(op.args.at(1), context);
    case OpCode::MULTIPLY:
        return resolve_value(op.args.at(0), context) * resolve_value(op.args.at(1), context);
    case OpCode::DIVIDE:
    {
        double denominator = resolve_value(op.args.at(1), context);
        if (denominator == 0)
            throw std::runtime_error("Division by zero.");
        return resolve_value(op.args.at(0), context) / denominator;
    }
    case OpCode::POWER:
        return std::pow(resolve_value(op.args.at(0), context), resolve_value(op.args.at(1), context));
    case OpCode::LOG:
        return std::log(resolve_value(op.args.at(0), context));
    case OpCode::LOG10:
        return std::log10(resolve_value(op.args.at(0), context));
    case OpCode::EXP:
        return std::exp(resolve_value(op.args.at(0), context));
    case OpCode::SIN:
        return std::sin(resolve_value(op.args.at(0), context));
    case OpCode::COS:
        return std::cos(resolve_value(op.args.at(0), context));
    case OpCode::TAN:
        return std::tan(resolve_value(op.args.at(0), context));
    default:
        throw std::runtime_error("Unsupported or unknown op_code during evaluation.");
    }
}

// Parses the entire JSON recipe file into the m_recipe struct.
void SimulationEngine::parse_recipe()
{
    std::ifstream file_stream(m_recipe_path);
    if (!file_stream.is_open())
    {
        throw std::runtime_error("Failed to open recipe file: " + m_recipe_path);
    }

    json recipe_json = json::parse(file_stream);

    m_recipe.num_trials = recipe_json.at("simulation_config").at("num_trials");
    m_recipe.output_variable = recipe_json.at("output_variable");

    for (const auto &[name, input_json] : recipe_json.at("inputs").items())
    {
        InputVariable var;
        var.type = input_json.at("type");

        if (var.type == "fixed")
        {
            var.fixed_value = input_json.at("value");
        }
        else if (var.type == "distribution")
        {
            var.dist_name = input_json.at("dist_name");
            var.dist_params = input_json.at("params").get<DistributionParams>();

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
            default:
                throw std::runtime_error("Unknown distribution type in recipe: " + var.dist_name);
            }
        }
        m_recipe.inputs[name] = var;
    }

    for (const auto &op_json : recipe_json.at("operations"))
    {
        Operation op;
        op.op_code = string_to_opcode(op_json.at("op_code"));
        op.result_name = op_json.at("result");
        op.args = op_json.at("args");
        m_recipe.operations.push_back(op);
    }

    std::cout << "Recipe parsing complete." << std::endl;
}