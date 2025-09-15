#pragma once

#include "include/engine/core/IExecutionStep.h"
#include "include/engine/core/IExecutable.h"

// --- Concrete Step for `let x = 123.45` ---
class LiteralAssignmentStep : public IExecutionStep
{
public:
    LiteralAssignmentStep(size_t result_index, TrialValue value);
    void execute(TrialContext &context) const override;

private:
    size_t m_result_index;
    TrialValue m_value;
};

// --- Helper for building and executing argument plans ---
struct ArgumentPlanner
{
    // Forward declarations for recursive structures
    struct NestedFunctionCall;
    struct NestedConditional;

    // An argument is pre-resolved into one of four things:
    using ResolvedArgument = std::variant<TrialValue, size_t, std::unique_ptr<NestedFunctionCall>, std::unique_ptr<NestedConditional>>;
    using ExecutableFactory = std::unordered_map<std::string, std::function<std::unique_ptr<IExecutable>()>>;

    // Structure to hold the plan for a nested function call
    struct NestedFunctionCall
    {
        std::unique_ptr<IExecutable> logic;
        std::vector<ResolvedArgument> args;
        std::string function_name;
        int line_num;
    };

    // Structure to hold the plan for a nested conditional expression
    struct NestedConditional
    {
        ResolvedArgument condition;
        ResolvedArgument then_expr;
        ResolvedArgument else_expr;
        int line_num;
    };

    // Helper to build the execution plan during construction (runs once).
    static ResolvedArgument build_argument_plan(const nlohmann::json &arg, const ExecutableFactory &factory);

    // Helper to execute the plan at runtime (runs millions of times).
    static TrialValue resolve_runtime_value(const ResolvedArgument &arg, const TrialContext &context);
};

// --- Concrete Step for `let x = add(y, z)` OR `let a, b = func(y, z)` ---
// This class is unified and handles both single and multi-assignment.
class ExecutionAssignmentStep : public IExecutionStep
{
public:
    ExecutionAssignmentStep(
        std::vector<size_t> result_indices, // Now always takes a vector of indices.
        std::string function_name,
        int line_num,
        std::unique_ptr<IExecutable> logic,
        const nlohmann::json &args,
        const ArgumentPlanner::ExecutableFactory &factory);

    void execute(TrialContext &context) const override;

private:
    std::vector<size_t> m_result_indices; // Stores one or more indices.
    std::string m_function_name;
    int m_line_num;
    std::unique_ptr<IExecutable> m_logic;
    std::vector<ArgumentPlanner::ResolvedArgument> m_resolved_args;
};

// --- Concrete Step for `let x = if cond then expr1 else expr2` ---
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