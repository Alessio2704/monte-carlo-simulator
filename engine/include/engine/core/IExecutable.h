#pragma once
#include "DataStructures.h"
#include <vector>

class IExecutable
{
public:
    virtual ~IExecutable() = default;
    virtual std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const = 0;
};