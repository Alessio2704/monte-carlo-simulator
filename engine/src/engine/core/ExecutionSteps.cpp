#include "include/engine/core/ExecutionSteps.h"
#include "include/engine/core/EngineException.h"
#include <stdexcept>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// ============================================================================
// == LiteralAssignmentStep
// ============================================================================

LiteralAssignmentStep::LiteralAssignmentStep(size_t result_index, TrialValue value)
    : m_result_index(result_index), m_value(std::move(value)) {}

void LiteralAssignmentStep::execute(TrialContext &context) const
{
    context[m_result_index] = m_value;
}

// ============================================================================
// == ArgumentPlanner
// ============================================================================

// This function runs AT RUNTIME to execute the plan.
TrialValue ArgumentPlanner::resolve_runtime_value(const ResolvedArgument &arg, const TrialContext &context)
{
    return std::visit(
        [&](auto &&plan) -> TrialValue
        {
            using T = std::decay_t<decltype(plan)>;
            if constexpr (std::is_same_v<T, TrialValue>)
            {
                return plan; // It's a literal value.
            }
            else if constexpr (std::is_same_v<T, size_t>)
            {
                return context.at(plan); // It's a variable index.
            }
            else if constexpr (std::is_same_v<T, std::unique_ptr<NestedFunctionCall>>)
            {
                const auto &nested_call = *plan;
                std::vector<TrialValue> nested_final_args;
                nested_final_args.reserve(nested_call.args.size());
                for (const auto &nested_arg_plan : nested_call.args)
                {
                    nested_final_args.push_back(resolve_runtime_value(nested_arg_plan, context));
                }
                try
                {
                    return nested_call.logic->execute(nested_final_args);
                }
                catch (const EngineException &e)
                {
                    // Re-throw exception, adding our contextual information.
                    throw EngineException(e.code(), std::string("In nested function '") + nested_call.function_name + "': " + e.what(), nested_call.line_num);
                }
                catch (const std::exception &e)
                {
                    throw EngineException(EngineErrc::UnknownError, std::string("In nested function '") + nested_call.function_name + "': " + e.what(), nested_call.line_num);
                }
            }
            else if constexpr (std::is_same_v<T, std::unique_ptr<NestedConditional>>)
            {
                const auto &nested_cond = *plan;
                try
                {
                    TrialValue condition_result = resolve_runtime_value(nested_cond.condition, context);
                    if (!std::holds_alternative<bool>(condition_result))
                    {
                        throw EngineException(EngineErrc::ConditionNotBoolean, "The 'if' condition did not evaluate to a boolean value.");
                    }
                    if (std::get<bool>(condition_result))
                    {
                        return resolve_runtime_value(nested_cond.then_expr, context);
                    }
                    else
                    {
                        return resolve_runtime_value(nested_cond.else_expr, context);
                    }
                }
                catch (const EngineException &e)
                {
                    throw EngineException(e.code(), std::string("In nested conditional expression: ") + e.what(), nested_cond.line_num);
                }
                catch (const std::exception &e)
                {
                    throw EngineException(EngineErrc::UnknownError, std::string("In nested conditional expression: ") + e.what(), nested_cond.line_num);
                }
            }
        },
        arg);
}

// This function runs ONCE AT CONSTRUCTION to build the execution plan.
ArgumentPlanner::ResolvedArgument ArgumentPlanner::build_argument_plan(
    const json &arg,
    const ExecutableFactory &factory)
{
    const auto &type_it = arg.find("type");
    if (type_it == arg.end())
    {
        throw EngineException(EngineErrc::RecipeParseError, "Argument object is missing 'type' field.");
    }
    const std::string &type = type_it->get<std::string>();

    if (type == "scalar_literal")
    {
        return TrialValue(arg.at("value").get<double>());
    }
    if (type == "boolean_literal")
    {
        return TrialValue(arg.at("value").get<bool>());
    }
    if (type == "vector_literal")
    {
        return TrialValue(arg.at("value").get<std::vector<double>>());
    }
    if (type == "string_literal")
    {
        return TrialValue(arg.at("value").get<std::string>());
    }
    if (type == "variable_index")
    {
        return arg.at("value").get<size_t>();
    }
    if (type == "execution_assignment")
    {
        auto nested_call = std::make_unique<NestedFunctionCall>();
        nested_call->line_num = arg.value("line", -1);
        nested_call->function_name = arg.at("function");
        auto it = factory.find(nested_call->function_name);
        if (it == factory.end())
        {
            throw EngineException(EngineErrc::UnknownFunction, "Unknown nested function: " + nested_call->function_name, nested_call->line_num);
        }
        nested_call->logic = it->second();
        const auto &nested_args_json = arg.at("args");
        nested_call->args.reserve(nested_args_json.size());
        for (const auto &nested_arg_json : nested_args_json)
        {
            nested_call->args.push_back(build_argument_plan(nested_arg_json, factory));
        }
        return nested_call;
    }
    if (type == "conditional_expression")
    {
        auto nested_cond = std::make_unique<NestedConditional>();
        nested_cond->line_num = arg.value("line", -1);
        nested_cond->condition = build_argument_plan(arg.at("condition"), factory);
        nested_cond->then_expr = build_argument_plan(arg.at("then_expr"), factory);
        nested_cond->else_expr = build_argument_plan(arg.at("else_expr"), factory);
        return nested_cond;
    }
    throw EngineException(EngineErrc::RecipeParseError, "Invalid argument type in bytecode: '" + type + "'.");
}

// ============================================================================
// == ExecutionAssignmentStep
// ============================================================================

ExecutionAssignmentStep::ExecutionAssignmentStep(
    size_t result_index,
    std::string function_name,
    int line_num,
    std::unique_ptr<IExecutable> logic,
    const json &args,
    const ArgumentPlanner::ExecutableFactory &factory)
    : m_result_index(result_index),
      m_function_name(std::move(function_name)),
      m_line_num(line_num),
      m_logic(std::move(logic))
{
    m_resolved_args.reserve(args.size());
    for (const auto &arg_json : args)
    {
        m_resolved_args.push_back(ArgumentPlanner::build_argument_plan(arg_json, factory));
    }
}

void ExecutionAssignmentStep::execute(TrialContext &context) const
{
    try
    {
        std::vector<TrialValue> final_args;
        final_args.reserve(m_resolved_args.size());
        for (const auto &arg_plan : m_resolved_args)
        {
            final_args.push_back(ArgumentPlanner::resolve_runtime_value(arg_plan, context));
        }

        context[m_result_index] = m_logic->execute(final_args);
    }
    catch (const std::out_of_range &e)
    {
        // Add specific catch for out_of_range to provide a better error code.
        throw EngineException(EngineErrc::IndexOutOfBounds, std::string("In function '") + m_function_name + "': " + "Variable index out of bounds.", m_line_num);
    }
    catch (const EngineException &e)
    {
        // This is a key location. We catch an exception from a function (like 'divide')
        // and add the line number and function name context before re-throwing.
        throw EngineException(e.code(), std::string("In function '") + m_function_name + "': " + e.what(), m_line_num);
    }
    catch (const std::exception &e)
    {
        // Fallback for any other unexpected standard exceptions.
        throw EngineException(EngineErrc::UnknownError, std::string("In function '") + m_function_name + "': " + e.what(), m_line_num);
    }
}

// ============================================================================
// == ConditionalAssignmentStep
// ============================================================================

ConditionalAssignmentStep::ConditionalAssignmentStep(
    size_t result_index,
    int line_num,
    const json &condition,
    const json &then_expr,
    const json &else_expr,
    const ArgumentPlanner::ExecutableFactory &factory)
    : m_result_index(result_index),
      m_line_num(line_num)
{
    m_condition_plan = ArgumentPlanner::build_argument_plan(condition, factory);
    m_then_plan = ArgumentPlanner::build_argument_plan(then_expr, factory);
    m_else_plan = ArgumentPlanner::build_argument_plan(else_expr, factory);
}

void ConditionalAssignmentStep::execute(TrialContext &context) const
{
    try
    {
        TrialValue condition_result = ArgumentPlanner::resolve_runtime_value(m_condition_plan, context);

        if (!std::holds_alternative<bool>(condition_result))
        {
            throw EngineException(EngineErrc::ConditionNotBoolean, "The 'if' condition did not evaluate to a boolean value.");
        }

        if (std::get<bool>(condition_result))
        {
            context[m_result_index] = ArgumentPlanner::resolve_runtime_value(m_then_plan, context);
        }
        else
        {
            context[m_result_index] = ArgumentPlanner::resolve_runtime_value(m_else_plan, context);
        }
    }
    catch (const EngineException &e)
    {
        throw EngineException(e.code(), std::string("In conditional expression: ") + e.what(), m_line_num);
    }
    catch (const std::exception &e)
    {
        throw EngineException(EngineErrc::UnknownError, std::string("In conditional expression: ") + e.what(), m_line_num);
    }
}