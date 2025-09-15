#pragma once
#include "include/engine/core/IExecutable.h"
#include "include/engine/functions/FunctionRegistry.h"

// --- Registration ---
// Each domain will have a single function to register all its operations.
void register_core_functions(FunctionRegistry &registry);

// --- Concrete Operation Classes ---

// Base class for variadic operations like add, subtract, multiply, etc.
class VariadicBaseOperation : public IExecutable
{
public:
    explicit VariadicBaseOperation(OpCode code);
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;

private:
    OpCode m_code;
};

// Base class for comparison operations like ==, >, <=, etc.
class ComparisonBaseOperation : public IExecutable
{
public:
    explicit ComparisonBaseOperation(OpCode code);
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;

private:
    OpCode m_code;
};

class AddOperation : public VariadicBaseOperation
{
public:
    AddOperation();
};
class SubtractOperation : public VariadicBaseOperation
{
public:
    SubtractOperation();
};
class MultiplyOperation : public VariadicBaseOperation
{
public:
    MultiplyOperation();
};
class DivideOperation : public VariadicBaseOperation
{
public:
    DivideOperation();
};
class PowerOperation : public VariadicBaseOperation
{
public:
    PowerOperation();
};

class LogOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class Log10Operation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class ExpOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class SinOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class CosOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class TanOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class IdentityOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};

class EqualsOperation : public ComparisonBaseOperation
{
public:
    EqualsOperation();
};
class NotEqualsOperation : public ComparisonBaseOperation
{
public:
    NotEqualsOperation();
};
class GreaterThanOperation : public ComparisonBaseOperation
{
public:
    GreaterThanOperation();
};
class LessThanOperation : public ComparisonBaseOperation
{
public:
    LessThanOperation();
};
class GreaterOrEqualOperation : public ComparisonBaseOperation
{
public:
    GreaterOrEqualOperation();
};
class LessOrEqualOperation : public ComparisonBaseOperation
{
public:
    LessOrEqualOperation();
};

class AndOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class OrOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};
class NotOperation : public IExecutable
{
public:
    std::vector<TrialValue> execute(const std::vector<TrialValue> &args) const override;
};