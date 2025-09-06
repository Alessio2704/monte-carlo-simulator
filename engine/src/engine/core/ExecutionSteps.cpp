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
      m_logic(std::move(logic))
{
    // Build the execution plan for all arguments here, once, during construction.
    m_resolved_args.reserve(args.size());
    for (const auto &arg_json : args)
    {
        m_resolved_args.push_back(build_argument_plan(arg_json, factory, variable_registry));
    }
}

void ExecutionAssignmentStep::execute(TrialContext &context) const
{
    try
    {
        // Resolve the final argument values by executing the pre-built plan.
        std::vector<TrialValue> final_args;
        final_args.reserve(m_resolved_args.size());
        for (const auto &arg_plan : m_resolved_args)
        {
            final_args.push_back(resolve_runtime_value(arg_plan, context));
        }

        TrialValue result = m_logic->execute(final_args);
        context[m_result_index] = std::move(result);
    }
    catch (const std::exception &e)
    {
        // This top-level error handler catches issues from the main function call.
        std::string error_prefix = "L" + std::to_string(m_line_num) + ": ";
        throw std::runtime_error(error_prefix + "In function '" + m_function_name + "': " + e.what());
    }
}

// This function runs AT RUNTIME to execute the plan. It's called recursively for nested functions.
TrialValue ExecutionAssignmentStep::resolve_runtime_value(const ResolvedArgument &arg, const TrialContext &context) const
{
    // Use a visitor to efficiently unpack the variant and perform the correct runtime action.
    return std::visit(
        [&](auto &&plan) -> TrialValue
        {
            using T = std::decay_t<decltype(plan)>;
            if constexpr (std::is_same_v<T, TrialValue>)
            {
                // The plan is just a literal value. Return it.
                return plan;
            }
            else if constexpr (std::is_same_v<T, size_t>)
            {
                // The plan is an index. Perform a fast lookup in the current trial's context.
                return context[plan];
            }
            else if constexpr (std::is_same_v<T, std::unique_ptr<NestedFunctionCall>>)
            {
                // The plan is a nested function call. We must execute it now.
                const auto &nested_call = *plan;
                std::vector<TrialValue> nested_final_args;
                nested_final_args.reserve(nested_call.args.size());

                // Recursively resolve the arguments for the nested call.
                for (const auto &nested_arg_plan : nested_call.args)
                {
                    nested_final_args.push_back(resolve_runtime_value(nested_arg_plan, context));
                }
                // Execute the nested function's logic.
                try
                {
                    return nested_call.logic->execute(nested_final_args);
                }
                catch (const std::exception &e)
                {
                    // This handler catches errors specifically from the nested function for better context.
                    std::string error_prefix = "L" + std::to_string(nested_call.line_num) + ": ";
                    throw std::runtime_error(error_prefix + "In nested function '" + nested_call.function_name + "': " + e.what());
                }
            }
        },
        arg);
}

// This function runs ONCE AT CONSTRUCTION to build the execution plan. It's called recursively for nested functions.
ExecutionAssignmentStep::ResolvedArgument ExecutionAssignmentStep::build_argument_plan(
    const json &arg,
    const ExecutableFactory &factory,
    const std::unordered_map<std::string, size_t> &variable_registry)
{
    if (arg.is_string())
    {
        const std::string &arg_str = arg.get<std::string>();
        auto it = variable_registry.find(arg_str);
        if (it != variable_registry.end())
        {
            // It's a variable. The plan is to look up its index at runtime.
            return it->second;
        }
        throw std::runtime_error("Argument '" + arg_str + "' is not a known variable.");
    }
    if (arg.is_number())
    {
        // It's a literal number. The plan is to simply return this value.
        return arg.get<double>();
    }
    if (arg.is_array())
    {
        // It's a literal array. The plan is to return this value.
        return arg.get<std::vector<double>>();
    }
    if (arg.is_object())
    {
        if (arg.contains("type") && arg.at("type") == "string_literal")
        {
            // It's a literal string. The plan is to return this value.
            return arg.at("value").get<std::string>();
        }

        // It's a nested function call. The plan is to create a NestedFunctionCall object.
        auto nested_call = std::make_unique<NestedFunctionCall>();
        nested_call->function_name = arg.at("function");
        nested_call->line_num = arg.value("line", -1);

        auto it = factory.find(nested_call->function_name);
        if (it == factory.end())
        {
            throw std::runtime_error("Unknown nested function: " + nested_call->function_name);
        }
        nested_call->logic = it->second();

        // Recursively build the plan for the nested function's arguments.
        const auto &nested_args_json = arg.at("args");
        nested_call->args.reserve(nested_args_json.size());
        for (const auto &nested_arg_json : nested_args_json)
        {
            nested_call->args.push_back(build_argument_plan(nested_arg_json, factory, variable_registry));
        }
        return nested_call;
    }
    throw std::runtime_error("Invalid argument type. Expected string, number, array, or object.");
}