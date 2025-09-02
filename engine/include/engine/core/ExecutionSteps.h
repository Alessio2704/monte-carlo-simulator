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

    ExecutionAssignmentStep(
        size_t result_index,
        std::unique_ptr<IExecutable> logic,
        const std::vector<json> &args,
        const ExecutableFactory &factory,
        const std::unordered_map<std::string, size_t> &variable_registry);
    void execute(TrialContext &context) const override;

private:
    size_t m_result_index;
    std::unique_ptr<IExecutable> m_logic;

    TrialValue resolve_value(const json &arg, const TrialContext &context) const;

    std::vector<json> m_args;
    const ExecutableFactory &m_factory_ref;
    const std::unordered_map<std::string, size_t> &m_variable_registry_ref;
};