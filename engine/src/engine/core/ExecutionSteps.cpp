#include "include/engine/core/ExecutionSteps.h"
#include <stdexcept>

// --- LiteralAssignmentStep ---

LiteralAssignmentStep::LiteralAssignmentStep(const std::string &result_name, TrialValue value)
    : m_result_name(result_name), m_value(std::move(value)) {}

void LiteralAssignmentStep::execute(TrialContext &context) const
{
    context[m_result_name] = m_value;
}

// --- ExecutionAssignmentStep ---

ExecutionAssignmentStep::ExecutionAssignmentStep(
    const std::string &result_name,
    std::unique_ptr<IExecutable> logic,
    const std::vector<json> &args,
    const ExecutableFactory &factory)
    : m_result_name(result_name),
      m_logic(std::move(logic)),
      m_args(args),
      m_factory_ref(factory)
{
}

void ExecutionAssignmentStep::execute(TrialContext &context) const
{
    std::vector<TrialValue> resolved_args;
    resolved_args.reserve(m_args.size());
    for (const auto &arg_json : m_args)
    {
        resolved_args.push_back(resolve_value_recursively(arg_json, context));
    }

    TrialValue result = m_logic->execute(resolved_args);
    context[m_result_name] = std::move(result);
}

TrialValue ExecutionAssignmentStep::resolve_value_recursively(const json &arg, const TrialContext &context) const
{
    if (arg.is_string())
    {
        const std::string &arg_str = arg.get<std::string>();
        auto it = context.find(arg_str);
        if (it != context.end())
        {
            return it->second;
        }
        throw std::runtime_error("Argument '" + arg_str + "' is not a known variable.");
    }
    if (arg.is_number())
    {
        return arg.get<double>();
    }
    if (arg.is_array())
    {
        return arg.get<std::vector<double>>();
    }

    if (arg.is_object())
    {
        // Handle string literals, which are passed as objects.
        if (arg.contains("type") && arg.at("type") == "string_literal")
        {
            return arg.at("value").get<std::string>();
        }

        // Handle nested function calls.
        std::string func_name = arg.at("function");
        auto it = m_factory_ref.find(func_name);
        if (it == m_factory_ref.end())
        {
            throw std::runtime_error("Unknown nested function: " + func_name);
        }
        // Create the executable for the nested function
        auto nested_logic = it->second();

        // Recursively resolve arguments for the NESTED function
        std::vector<TrialValue> nested_resolved_args;
        const auto &nested_args_json = arg.at("args");
        nested_resolved_args.reserve(nested_args_json.size());
        for (const auto &nested_arg_json : nested_args_json)
        {
            nested_resolved_args.push_back(resolve_value_recursively(nested_arg_json, context));
        }

        // Execute the nested function and return its result
        return nested_logic->execute(nested_resolved_args);
    }

    throw std::runtime_error("Invalid argument type. Expected string, number, array, or object.");
}