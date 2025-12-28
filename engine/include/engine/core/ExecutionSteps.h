#pragma once

#include "include/engine/core/IExecutionStep.h"
#include "include/engine/core/IExecutable.h"

class LiteralAssignmentStep : public IExecutionStep
{
public:
    LiteralAssignmentStep(size_t result_index, TrialValue value);
    void execute(TrialContext &context) const override;

private:
    size_t m_result_index;
    TrialValue m_value;
};

struct ArgumentPlanner
{
    struct NestedFunctionCall;
    struct NestedConditional;

    using ResolvedArgument = std::variant<TrialValue, size_t, std::unique_ptr<NestedFunctionCall>, std::unique_ptr<NestedConditional>>;
    using ExecutableFactory = std::unordered_map<std::string, std::function<std::unique_ptr<IExecutable>()>>;

    struct NestedFunctionCall
    {
        std::unique_ptr<IExecutable> logic;
        std::vector<ResolvedArgument> args;
        std::string function_name;
        int line_num;
    };

    struct NestedConditional
    {
        ResolvedArgument condition;
        ResolvedArgument then_expr;
        ResolvedArgument else_expr;
        int line_num;
    };

    static ResolvedArgument build_argument_plan(const nlohmann::json &arg, const ExecutableFactory &factory);

    static TrialValue resolve_runtime_value(const ResolvedArgument &arg, const TrialContext &context);
};

class ExecutionAssignmentStep : public IExecutionStep
{
public:
    ExecutionAssignmentStep(
        std::vector<size_t> result_indices,
        std::string function_name,
        int line_num,
        std::unique_ptr<IExecutable> logic,
        const nlohmann::json &args,
        const ArgumentPlanner::ExecutableFactory &factory);

    void execute(TrialContext &context) const override;

private:
    std::vector<size_t> m_result_indices;
    std::string m_function_name;
    int m_line_num;
    std::unique_ptr<IExecutable> m_logic;
    std::vector<ArgumentPlanner::ResolvedArgument> m_resolved_args;
};

class ConditionalAssignmentStep : public IExecutionStep
{
public:
    ConditionalAssignmentStep(
        size_t result_index,
        int line_num,
        const nlohmann::json &condition,
        const nlohmann::json &then_expr,
        const nlohmann::json &else_expr,
        const ArgumentPlanner::ExecutableFactory &factory);

    void execute(TrialContext &context) const override;

private:
    size_t m_result_index;
    int m_line_num;
    ArgumentPlanner::ResolvedArgument m_condition_plan;
    ArgumentPlanner::ResolvedArgument m_then_plan;
    ArgumentPlanner::ResolvedArgument m_else_plan;
};