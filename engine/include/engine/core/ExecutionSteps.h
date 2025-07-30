#pragma once

#include "include/engine/core/IExecutionStep.h"
#include "include/engine/core/IExecutable.h"
#include <string>
#include <vector>
#include <memory>
#include <functional>

// --- Concrete Step for `let x = 123.45` ---
class LiteralAssignmentStep : public IExecutionStep
{
public:
    LiteralAssignmentStep(const std::string &result_name, TrialValue value);

    void execute(TrialContext &context) const override;

private:
    std::string m_result_name;
    TrialValue m_value;
};

// --- Concrete Step for `let x = add(y, z)` ---
class ExecutionAssignmentStep : public IExecutionStep
{
public:
    // The factory type, defined here for convenience
    using ExecutableFactory = std::unordered_map<std::string, std::function<std::unique_ptr<IExecutable>()>>;

    ExecutionAssignmentStep(
        const std::string &result_name,
        std::unique_ptr<IExecutable> logic,
        const std::vector<json> &args,
        const ExecutableFactory &factory);

    void execute(TrialContext &context) const override;

private:
    std::string m_result_name;
    std::unique_ptr<IExecutable> m_logic;
    std::vector<json> m_args;
    const ExecutableFactory &m_factory_ref;

    TrialValue resolve_value_recursively(const json &arg, const TrialContext &context) const;
};