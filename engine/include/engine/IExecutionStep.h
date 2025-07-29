#pragma once

#include <string>
#include <unordered_map>
#include "datastructures.h"

using TrialContext = std::unordered_map<std::string, TrialValue>;

// Interface for a single step in the simulation's execution sequence.
class IExecutionStep
{
public:
    virtual ~IExecutionStep() = default;

    // The core contract for all steps.
    // Each step modifies the context in place.
    virtual void execute(TrialContext &context) const = 0;
};