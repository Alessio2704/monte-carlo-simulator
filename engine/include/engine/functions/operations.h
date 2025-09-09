#pragma once
#include "include/engine/core/IExecutable.h"

// Base class for variadic operations like add, subtract, multiply, etc.
class VariadicBaseOperation : public IExecutable
{
public:
    explicit VariadicBaseOperation(OpCode code);
    TrialValue execute(const std::vector<TrialValue> &args) const override;

private:
    OpCode m_code;
};

// Base class for comparison operations like ==, >, <=, etc.
class ComparisonBaseOperation : public IExecutable
{
public:
    explicit ComparisonBaseOperation(OpCode code);
    TrialValue execute(const std::vector<TrialValue> &args) const override;

private:
    OpCode m_code;
};

// --- Concrete Operation Classes ---

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
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class Log10Operation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class ExpOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class SinOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class CosOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class TanOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class IdentityOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};

// --- Comparison and Logical Operations ---
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
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class OrOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class NotOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};

// --- Vector and Series Operations ---
class GrowSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class CompoundSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class NpvOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class SumSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class GetElementOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class DeleteElementOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class SeriesDeltaOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class ComposeVectorOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class InterpolateSeriesOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
class CapitalizeExpenseOperation : public IExecutable
{
public:
    TrialValue execute(const std::vector<TrialValue> &args) const override;
};
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