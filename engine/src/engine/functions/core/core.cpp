#include "include/engine/functions/core/operations.h"
#include "include/engine/core/EngineException.h"
#include <vector>
#include <numeric>
#include <cmath>

// --- Registration Function ---

void register_core_functions(FunctionRegistry &registry)
{
    // Math
    registry.register_function("add", []
                               { return std::make_unique<AddOperation>(); });
    registry.register_function("subtract", []
                               { return std::make_unique<SubtractOperation>(); });
    registry.register_function("multiply", []
                               { return std::make_unique<MultiplyOperation>(); });
    registry.register_function("divide", []
                               { return std::make_unique<DivideOperation>(); });
    registry.register_function("power", []
                               { return std::make_unique<PowerOperation>(); });
    registry.register_function("log", []
                               { return std::make_unique<LogOperation>(); });
    registry.register_function("log10", []
                               { return std::make_unique<Log10Operation>(); });
    registry.register_function("exp", []
                               { return std::make_unique<ExpOperation>(); });
    registry.register_function("sin", []
                               { return std::make_unique<SinOperation>(); });
    registry.register_function("cos", []
                               { return std::make_unique<CosOperation>(); });
    registry.register_function("tan", []
                               { return std::make_unique<TanOperation>(); });
    registry.register_function("identity", []
                               { return std::make_unique<IdentityOperation>(); });

    // Comparison & Logical
    registry.register_function("__eq__", []
                               { return std::make_unique<EqualsOperation>(); });
    registry.register_function("__neq__", []
                               { return std::make_unique<NotEqualsOperation>(); });
    registry.register_function("__gt__", []
                               { return std::make_unique<GreaterThanOperation>(); });
    registry.register_function("__lt__", []
                               { return std::make_unique<LessThanOperation>(); });
    registry.register_function("__gte__", []
                               { return std::make_unique<GreaterOrEqualOperation>(); });
    registry.register_function("__lte__", []
                               { return std::make_unique<LessOrEqualOperation>(); });
    registry.register_function("__and__", []
                               { return std::make_unique<AndOperation>(); });
    registry.register_function("__or__", []
                               { return std::make_unique<OrOperation>(); });
    registry.register_function("__not__", []
                               { return std::make_unique<NotOperation>(); });
}

// --- Math Operations Implementations ---

// =====================================================================================
// == SIMD-FRIENDLY "FAST PATH" HELPERS
// =====================================================================================
// These simple, standalone functions contain loops that modern C++ compilers
// can easily auto-vectorize into high-performance SIMD instructions (e.g., AVX, SSE).

// --- Vector-Vector Operations ---
inline std::vector<double> add_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = left[i] + right[i];
    }
    return result;
}
inline std::vector<double> subtract_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = left[i] - right[i];
    }
    return result;
}
inline std::vector<double> multiply_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = left[i] * right[i];
    }
    return result;
}
inline std::vector<double> divide_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        if (right[i] == 0.0)
            throw EngineException(EngineErrc::DivisionByZero, "Division by zero in vector operation.");
        result[i] = left[i] / right[i];
    }
    return result;
}
inline std::vector<double> power_vectors_simd(const std::vector<double> &left, const std::vector<double> &right)
{
    std::vector<double> result(left.size());
    for (size_t i = 0; i < left.size(); ++i)
    {
        result[i] = std::pow(left[i], right[i]);
    }
    return result;
}

// --- Vector-Scalar Operations ---
inline std::vector<double> add_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] + scalar;
    }
    return result;
}
inline std::vector<double> subtract_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] - scalar;
    }
    return result;
}
inline std::vector<double> multiply_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] * scalar;
    }
    return result;
}
inline std::vector<double> divide_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    if (scalar == 0.0)
        throw EngineException(EngineErrc::DivisionByZero, "Division by zero.");
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = vec[i] / scalar;
    }
    return result;
}
inline std::vector<double> power_vector_scalar_simd(const std::vector<double> &vec, double scalar)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = std::pow(vec[i], scalar);
    }
    return result;
}

// --- Scalar-Vector Operations ---
inline std::vector<double> add_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = scalar + vec[i];
    }
    return result;
}
inline std::vector<double> subtract_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = scalar - vec[i];
    }
    return result;
}
inline std::vector<double> multiply_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = scalar * vec[i];
    }
    return result;
}
inline std::vector<double> divide_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        if (vec[i] == 0.0)
            throw EngineException(EngineErrc::DivisionByZero, "Division by zero.");
        result[i] = scalar / vec[i];
    }
    return result;
}
inline std::vector<double> power_scalar_vector_simd(double scalar, const std::vector<double> &vec)
{
    std::vector<double> result(vec.size());
    for (size_t i = 0; i < vec.size(); ++i)
    {
        result[i] = std::pow(scalar, vec[i]);
    }
    return result;
}

// =====================================================================================
// == GENERIC "SLOW PATH" HELPERS
// =====================================================================================

inline double perform_variadic_op(OpCode code, const std::vector<double> &values)
{
    if (values.empty())
        throw EngineException(EngineErrc::EmptyVectorOperation, "Cannot perform operation on an empty list of values.");
    double accumulator = values[0];
    for (size_t i = 1; i < values.size(); ++i)
    {
        switch (code)
        {
        case OpCode::ADD:
            accumulator += values[i];
            break;
        case OpCode::SUBTRACT:
            accumulator -= values[i];
            break;
        case OpCode::MULTIPLY:
            accumulator *= values[i];
            break;
        case OpCode::DIVIDE:
            if (values[i] == 0.0)
                throw EngineException(EngineErrc::DivisionByZero, "Division by zero");
            accumulator /= values[i];
            break;
        case OpCode::POWER:
            accumulator = std::pow(accumulator, values[i]);
            break;
        default:
            throw EngineException(EngineErrc::UnknownError, "Unsupported variadic op code.");
        }
    }
    return accumulator;
}

struct ElementWiseVisitor
{
    OpCode code;

    // --- Valid Numeric Operations ---
    TrialValue operator()(double left, double right) const { return perform_variadic_op(code, {left, right}); }

    TrialValue operator()(const std::vector<double> &vec, double scalar) const
    {
        std::vector<double> result;
        result.reserve(vec.size());
        for (double val : vec)
        {
            result.push_back(perform_variadic_op(code, {val, scalar}));
        }
        return result;
    }

    TrialValue operator()(double scalar, const std::vector<double> &vec) const
    {
        std::vector<double> result;
        result.reserve(vec.size());
        for (double val : vec)
        {
            result.push_back(perform_variadic_op(code, {scalar, val}));
        }
        return result;
    }

    TrialValue operator()(const std::vector<double> &vec_left, const std::vector<double> &vec_right) const
    {
        if (vec_left.size() != vec_right.size())
            throw EngineException(EngineErrc::VectorSizeMismatch, "Vector size mismatch: element-wise operation requires vectors of the same length, but got sizes " + std::to_string(vec_left.size()) + " and " + std::to_string(vec_right.size()) + ".");
        std::vector<double> result;
        result.reserve(vec_left.size());
        for (size_t i = 0; i < vec_left.size(); ++i)
        {
            result.push_back(perform_variadic_op(code, {vec_left[i], vec_right[i]}));
        }
        return result;
    }

    // --- Catch-all for Invalid Type Combinations ---
    // This template handles any combination not explicitly defined above (e.g., string+double, bool+vector, etc.).
    // It makes the visitor exhaustive, satisfying the requirement of std::visit.
    template <typename T1, typename T2>
    TrialValue operator()(const T1 &, const T2 &) const
    {
        throw EngineException(EngineErrc::MismatchedArgumentType, "Unsupported argument types for mathematical operation.");
    }
};

// =====================================================================================
// == IExecutable Implementations with Fast Path Dispatcher
// =====================================================================================

VariadicBaseOperation::VariadicBaseOperation(OpCode code) : m_code(code) {}

// --- HELPER FOR IN-PLACE VECTOR OPERATIONS ---
// This visitor will modify the `accumulator` directly, avoiding new allocations.
struct InPlaceVisitor
{
    OpCode code;
    TrialValue &accumulator;

    // Vector-Vector
    void operator()(const std::vector<double> &right) const
    {
        auto &acc_vec = std::get<std::vector<double>>(accumulator);
        if (acc_vec.size() != right.size())
            throw EngineException(EngineErrc::VectorSizeMismatch, "Vector size mismatch for in-place operation.");
        for (size_t i = 0; i < acc_vec.size(); ++i)
        {
            switch (code)
            {
            case OpCode::ADD:
                acc_vec[i] += right[i];
                break;
            case OpCode::SUBTRACT:
                acc_vec[i] -= right[i];
                break;
            case OpCode::MULTIPLY:
                acc_vec[i] *= right[i];
                break;
            case OpCode::DIVIDE:
                if (right[i] == 0.0)
                    throw EngineException(EngineErrc::DivisionByZero, "Division by zero.");
                acc_vec[i] /= right[i];
                break;
            case OpCode::POWER:
                acc_vec[i] = std::pow(acc_vec[i], right[i]);
                break;
            default:
                throw EngineException(EngineErrc::UnknownError, "Unsupported in-place op code.");
            }
        }
    }

    // Vector-Scalar
    void operator()(double right) const
    {
        auto &acc_vec = std::get<std::vector<double>>(accumulator);
        for (size_t i = 0; i < acc_vec.size(); ++i)
        {
            switch (code)
            {
            case OpCode::ADD:
                acc_vec[i] += right;
                break;
            case OpCode::SUBTRACT:
                acc_vec[i] -= right;
                break;
            case OpCode::MULTIPLY:
                acc_vec[i] *= right;
                break;
            case OpCode::DIVIDE:
                if (right == 0.0)
                    throw EngineException(EngineErrc::DivisionByZero, "Division by zero.");
                acc_vec[i] /= right;
                break;
            case OpCode::POWER:
                acc_vec[i] = std::pow(acc_vec[i], right);
                break;
            default:
                throw EngineException(EngineErrc::UnknownError, "Unsupported in-place op code.");
            }
        }
    }

    // Catch-all for unsupported types (string, bool, etc.)
    template <typename T>
    void operator()(const T &) const
    {
        throw EngineException(EngineErrc::MismatchedArgumentType, "Unsupported argument type for variadic math operation.");
    }
};

TrialValue VariadicBaseOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.empty())
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Operation requires at least one argument.");

    // Start with the first argument as the initial result.
    TrialValue accumulator = args[0];

    // Determine if any argument is a vector, which dictates the overall strategy.
    bool has_vector = std::any_of(args.begin(), args.end(), [](const TrialValue &v)
                                  { return std::holds_alternative<std::vector<double>>(v); });

    if (!has_vector)
    {
        // --- SCALAR-ONLY FAST PATH ---
        // All arguments are doubles, no vectors involved.
        double result = std::get<double>(accumulator);
        for (size_t i = 1; i < args.size(); ++i)
        {
            double val = std::get<double>(args[i]);
            switch (m_code)
            {
            case OpCode::ADD:
                result += val;
                break;
            case OpCode::SUBTRACT:
                result -= val;
                break;
            case OpCode::MULTIPLY:
                result *= val;
                break;
            case OpCode::DIVIDE:
                if (val == 0.0)
                    throw EngineException(EngineErrc::DivisionByZero, "Division by zero");
                result /= val;
                break;
            case OpCode::POWER:
                result = std::pow(result, val);
                break;
            default:
                throw EngineException(EngineErrc::UnknownError, "Unsupported variadic op code.");
            }
        }
        return result;
    }

    // --- VECTOR/MIXED-TYPE OPTIMIZED PATH ---
    // At least one argument is a vector. The result must be a vector.
    // If the initial accumulator is a scalar, we must "promote" it to a vector.
    if (std::holds_alternative<double>(accumulator))
    {
        double scalar_val = std::get<double>(accumulator);
        // Find the first vector in the args to determine the required size.
        size_t vector_size = 0;
        for (const auto &arg : args)
        {
            if (std::holds_alternative<std::vector<double>>(arg))
            {
                vector_size = std::get<std::vector<double>>(arg).size();
                break;
            }
        }
        // Promote the scalar to a vector of the correct size.
        accumulator = std::vector<double>(vector_size, scalar_val);
    }

    // Loop through the rest of the arguments, applying the operation in-place.
    for (size_t i = 1; i < args.size(); ++i)
    {
        // We visit the current argument and apply the operation to our accumulator.
        std::visit(InPlaceVisitor{m_code, accumulator}, args[i]);
    }

    return accumulator;
}

AddOperation::AddOperation() : VariadicBaseOperation(OpCode::ADD) {}
SubtractOperation::SubtractOperation() : VariadicBaseOperation(OpCode::SUBTRACT) {}
MultiplyOperation::MultiplyOperation() : VariadicBaseOperation(OpCode::MULTIPLY) {}
DivideOperation::DivideOperation() : VariadicBaseOperation(OpCode::DIVIDE) {}
PowerOperation::PowerOperation() : VariadicBaseOperation(OpCode::POWER) {}

TrialValue LogOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'log' requires 1 argument.");
    return std::log(std::get<double>(args[0]));
}
TrialValue Log10Operation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'log10' requires 1 argument.");
    return std::log10(std::get<double>(args[0]));
}
TrialValue ExpOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'exp' requires 1 argument.");
    return std::exp(std::get<double>(args[0]));
}
TrialValue SinOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'sin' requires 1 argument.");
    return std::sin(std::get<double>(args[0]));
}
TrialValue CosOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'cos' requires 1 argument.");
    return std::cos(std::get<double>(args[0]));
}
TrialValue TanOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'tan' requires 1 argument.");
    return std::tan(std::get<double>(args[0]));
}
TrialValue IdentityOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 1)
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'identity' requires exactly 1 argument.");
    return args[0];
}

// --- Comparison and Logical Operations Implementations ---

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