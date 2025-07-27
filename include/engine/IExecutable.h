#pragma once
#include "engine/datastructures.h"
#include <vector>

// Unified interface for any logic that takes arguments and returns a value.
// Both operations (like Add) and samplers (like Normal) will implement this.
class IExecutable
{
public:
    virtual ~IExecutable() = default;
    virtual TrialValue execute(const std::vector<TrialValue> &args) const = 0;
};