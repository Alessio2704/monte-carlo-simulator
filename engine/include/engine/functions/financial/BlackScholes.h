#pragma once
#include "include/engine/core/IExecutable.h"

class BlackScholesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};