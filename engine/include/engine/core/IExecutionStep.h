#pragma once

#include <string>
#include "include/engine/core/datastructures.h"

using TrialContext = std::vector<TrialValue>;

// Interface for a single step in the simulation's execution sequence.
class IExecutionStep
{
public:
    virtual ~IExecutionStep() = default;

    // The core contract for all steps.
    // Each step modifies the context in place.
    virtual void execute(TrialContext &context) const = 0;
};