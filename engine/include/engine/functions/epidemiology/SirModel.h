#pragma once
#include "include/engine/core/IExecutable.h"

class SirModelOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};