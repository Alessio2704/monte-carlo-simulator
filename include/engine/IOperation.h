#pragma once
#include "engine/datastructures.h"
#include <vector>

class IOperation
{
public:
    virtual ~IOperation() = default;

    // The "execute" method is the contract for all operation classes.
    // It takes the arguments and the context and returns the result.
    virtual TrialValue execute(const std::vector<TrialValue> &args) const = 0;
};