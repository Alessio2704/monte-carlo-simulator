#pragma once

#include <string>
#include "include/engine/core/DataStructures.h"

using TrialContext = std::vector<TrialValue>;

class IExecutionStep
{
public:
    virtual ~IExecutionStep() = default;

    virtual void execute(TrialContext &context) const = 0;
};