#pragma once
#include "include/engine/core/IExecutable.h"
#include "include/engine/functions/FunctionRegistry.h"

// --- Registration ---
void register_io_functions(FunctionRegistry &registry);

// --- Concrete Operation Classes ---
class ReadCsvVectorOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class ReadCsvScalarOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};