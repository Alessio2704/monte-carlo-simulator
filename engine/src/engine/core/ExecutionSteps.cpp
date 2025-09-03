#include "include/engine/core/ExecutionSteps.h"
#include <stdexcept>

LiteralAssignmentStep::LiteralAssignmentStep(size_t result_index, TrialValue value)
    : m_result_index(result_index), m_value(std::move(value)) {}

void LiteralAssignmentStep::execute(TrialContext &context) const
{
    context[m_result_index] = m_value;
}

ExecutionAssignmentStep::ExecutionAssignmentStep(
    size_t result_index,
    std::string function_name,
    int line_num,
    std::unique_ptr<IExecutable> logic,
    const std::vector<json> &args,
    const ExecutableFactory &factory,
    const std::unordered_map<std::string, size_t> &variable_registry)
    : m_result_index(result_index),
      m_function_name(std::move(function_name)),
      m_line_num(line_num),
      m_logic(std::move(logic)),
      m_args(args),
      m_factory_ref(factory),
      m_variable_registry_ref(variable_registry)
{
}

void ExecutionAssignmentStep::execute(TrialContext &context) const
{
    try
    {
        std::vector<TrialValue> resolved_args;
        resolved_args.reserve(m_args.size());
        for (const auto &arg_json : m_args)
        {
            resolved_args.push_back(resolve_value(arg_json, context));
        }
        TrialValue result = m_logic->execute(resolved_args);
        context[m_result_index] = std::move(result);
    }
    catch (const std::exception &e)
    {
        std::string error_prefix = "L" + std::to_string(m_line_num) + ": ";
        throw std::runtime_error(error_prefix + "In function '" + m_function_name + "': " + e.what());
    }
}

TrialValue ExecutionAssignmentStep::resolve_value(const json &arg, const TrialContext &context) const
{
    if (arg.is_string())
    {
        const std::string &arg_str = arg.get<std::string>();
        auto it = m_variable_registry_ref.find(arg_str);
        if (it != m_variable_registry_ref.end())
        {
            return context[it->second];
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
        if (arg.contains("type") && arg.at("type") == "string_literal")
        {
            return arg.at("value").get<std::string>();
        }
        std::string func_name = arg.at("function");
        auto it = m_factory_ref.find(func_name);
        if (it == m_factory_ref.end())
        {
            throw std::runtime_error("Unknown nested function: " + func_name);
        }
        auto nested_logic = it->second();
        std::vector<TrialValue> nested_resolved_args;
        const auto &nested_args_json = arg.at("args");
        nested_resolved_args.reserve(nested_args_json.size());
        for (const auto &nested_arg_json : nested_args_json)
        {
            nested_resolved_args.push_back(resolve_value(nested_arg_json, context));
        }
        return nested_logic->execute(nested_resolved_args);
    }
    throw std::runtime_error("Invalid argument type. Expected string, number, array, or object.");
}