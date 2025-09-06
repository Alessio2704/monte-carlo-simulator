#pragma once

#include "include/engine/core/IExecutionStep.h"
#include "include/engine/core/IExecutable.h"
#include <string>
#include <vector>
#include <memory>
#include <functional>
#include <variant>

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

// --- Concrete Step for `let x = add(y, z)` ---
class ExecutionAssignmentStep : public IExecutionStep
{
public:
    using ExecutableFactory = std::unordered_map<std::string, std::function<std::unique_ptr<IExecutable>()>>;

    // Forward declaration for recursive structure
    struct NestedFunctionCall;

    // An argument is pre-resolved into one of three things:
    // 1. A literal value (double, vector<double>, string).
    // 2. An index to a variable that must be fetched from the context at runtime.
    // 3. A pointer to another function call that must be executed at runtime.
    using ResolvedArgument = std::variant<TrialValue, size_t, std::unique_ptr<NestedFunctionCall>>;

    // Structure to hold the plan for a nested function call
    struct NestedFunctionCall
    {
        std::unique_ptr<IExecutable> logic;
        std::vector<ResolvedArgument> args;
        // Metadata for better error messages
        std::string function_name;
        int line_num;
    };

    ExecutionAssignmentStep(
        size_t result_index,
        std::string function_name,
        int line_num,
        std::unique_ptr<IExecutable> logic,
        const std::vector<json> &args,
        const ExecutableFactory &factory,
        const std::unordered_map<std::string, size_t> &variable_registry);

    void execute(TrialContext &context) const override;

private:
    size_t m_result_index;
    std::string m_function_name;
    int m_line_num;
    std::unique_ptr<IExecutable> m_logic;
    std::vector<ResolvedArgument> m_resolved_args; // The pre-compiled execution plan for the step's arguments.

    // Helper to build the execution plan during construction (runs once).
    static ResolvedArgument build_argument_plan(
        const json &arg,
        const ExecutableFactory &factory,
        const std::unordered_map<std::string, size_t> &variable_registry);

    // Helper to execute the plan at runtime (runs millions of times).
    TrialValue resolve_runtime_value(const ResolvedArgument &arg, const TrialContext &context) const;
};