#include "include/engine/functions/operations.h"
#include "include/engine/core/EngineException.h"
#include <vector>

ComparisonBaseOperation::ComparisonBaseOperation(OpCode code) : m_code(code) {}

TrialValue ComparisonBaseOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 2)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Comparison operator requires 2 arguments.");
    return std::visit([this](auto &&left, auto &&right) -> TrialValue
                      {
        using T1 = std::decay_t<decltype(left)>;
        using T2 = std::decay_t<decltype(right)>;

        if constexpr (std::is_same_v<T1, double> && std::is_same_v<T2, double>) {
            switch (m_code) {
                case OpCode::EQ:  return left == right;
                case OpCode::NEQ: return left != right;
                case OpCode::GT:  return left > right;
                case OpCode::LT:  return left < right;
                case OpCode::GTE: return left >= right;
                case OpCode::LTE: return left <= right;
                default: throw EngineException(EngineErrc::UnknownError, "Invalid comparison opcode for scalars.");
            }
        } else if constexpr (std::is_same_v<T1, bool> && std::is_same_v<T2, bool>) {
            switch (m_code) {
                case OpCode::EQ:  return left == right;
                case OpCode::NEQ: return left != right;
                default: throw EngineException(EngineErrc::MismatchedArgumentType, "Only equality operators (==, !=) are supported for booleans.");
            }
        } else {
            // Fallback for non-matching types: only allow equality checks
            switch(m_code) {
                case OpCode::EQ: return false;
                case OpCode::NEQ: return true;
                default: throw EngineException(EngineErrc::MismatchedArgumentType, "Unsupported types for this comparison.");
            }
        } }, args[0], args[1]);
}

EqualsOperation::EqualsOperation() : ComparisonBaseOperation(OpCode::EQ) {}
NotEqualsOperation::NotEqualsOperation() : ComparisonBaseOperation(OpCode::NEQ) {}
GreaterThanOperation::GreaterThanOperation() : ComparisonBaseOperation(OpCode::GT) {}
LessThanOperation::LessThanOperation() : ComparisonBaseOperation(OpCode::LT) {}
GreaterOrEqualOperation::GreaterOrEqualOperation() : ComparisonBaseOperation(OpCode::GTE) {}
LessOrEqualOperation::LessOrEqualOperation() : ComparisonBaseOperation(OpCode::LTE) {}

TrialValue AndOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.empty())
        throw EngineException(EngineErrc::IncorrectArgumentCount, "'and' operator requires at least one argument.");
    for (const auto &arg : args)
    {
        if (!std::holds_alternative<bool>(arg))
            throw EngineException(EngineErrc::LogicalOperatorRequiresBoolean, "'and' operator requires a boolean argument.");
        if (!std::get<bool>(arg))
            return false;
    }
    return true;
}

TrialValue OrOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.empty())
        throw EngineException(EngineErrc::IncorrectArgumentCount, "'or' operator requires at least one argument.");
    for (const auto &arg : args)
    {
        if (!std::holds_alternative<bool>(arg))
            throw EngineException(EngineErrc::LogicalOperatorRequiresBoolean, "'or' operator requires a boolean argument.");
        if (std::get<bool>(arg))
            return true;
    }
    return false;
}

TrialValue NotOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "'not' operator requires 1 argument.");
    if (!std::holds_alternative<bool>(args[0]))
        throw EngineException(EngineErrc::LogicalOperatorRequiresBoolean, "'not' operator requires a boolean argument.");
    return !std::get<bool>(args[0]);
}