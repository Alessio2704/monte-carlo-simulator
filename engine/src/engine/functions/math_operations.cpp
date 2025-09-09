#include "include/engine/functions/operations.h"
#include "include/engine/core/EngineException.h"
#include <vector>
#include <numeric> // Required for std::accumulate

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

TrialValue VariadicBaseOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.empty())
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Operation requires at least one argument.");
    if (args.size() == 1)
        return args[0];

    // --- FAST PATH DISPATCHER ---
    if (args.size() == 2)
    {
        const auto &left = args[0];
        const auto &right = args[1];

        if (std::holds_alternative<std::vector<double>>(left) && std::holds_alternative<std::vector<double>>(right))
        {
            const auto &vec_left = std::get<std::vector<double>>(left);
            const auto &vec_right = std::get<std::vector<double>>(right);
            if (vec_left.size() != vec_right.size())
                throw EngineException(EngineErrc::VectorSizeMismatch, "Vector size mismatch: element-wise operation requires vectors of the same length, but got sizes " + std::to_string(vec_left.size()) + " and " + std::to_string(vec_right.size()) + ".");

            switch (m_code)
            {
            case OpCode::ADD:
                return add_vectors_simd(vec_left, vec_right);
            case OpCode::SUBTRACT:
                return subtract_vectors_simd(vec_left, vec_right);
            case OpCode::MULTIPLY:
                return multiply_vectors_simd(vec_left, vec_right);
            case OpCode::DIVIDE:
                return divide_vectors_simd(vec_left, vec_right);
            case OpCode::POWER:
                return power_vectors_simd(vec_left, vec_right);
            default:
                break;
            }
        }
        else if (std::holds_alternative<std::vector<double>>(left) && std::holds_alternative<double>(right))
        {
            const auto &vec = std::get<std::vector<double>>(left);
            double scalar = std::get<double>(right);
            switch (m_code)
            {
            case OpCode::ADD:
                return add_vector_scalar_simd(vec, scalar);
            case OpCode::SUBTRACT:
                return subtract_vector_scalar_simd(vec, scalar);
            case OpCode::MULTIPLY:
                return multiply_vector_scalar_simd(vec, scalar);
            case OpCode::DIVIDE:
                return divide_vector_scalar_simd(vec, scalar);
            case OpCode::POWER:
                return power_vector_scalar_simd(vec, scalar);
            default:
                break;
            }
        }
        else if (std::holds_alternative<double>(left) && std::holds_alternative<std::vector<double>>(right))
        {
            double scalar = std::get<double>(left);
            const auto &vec = std::get<std::vector<double>>(right);
            switch (m_code)
            {
            case OpCode::ADD:
                return add_scalar_vector_simd(scalar, vec);
            case OpCode::SUBTRACT:
                return subtract_scalar_vector_simd(scalar, vec);
            case OpCode::MULTIPLY:
                return multiply_scalar_vector_simd(scalar, vec);
            case OpCode::DIVIDE:
                return divide_scalar_vector_simd(scalar, vec);
            case OpCode::POWER:
                return power_scalar_vector_simd(scalar, vec);
            default:
                break;
            }
        }
    }

    // --- SLOW PATH (FALLBACK) ---
    bool has_vector = false;
    for (const auto &arg : args)
    {
        if (std::holds_alternative<std::vector<double>>(arg))
        {
            has_vector = true;
            break;
        }
    }

    if (!has_vector)
    {
        std::vector<double> values;
        values.reserve(args.size());
        for (const auto &arg : args)
            values.push_back(std::get<double>(arg));
        return perform_variadic_op(m_code, values);
    }

    TrialValue accumulator = args[0];
    for (size_t i = 1; i < args.size(); ++i)
    {
        accumulator = std::visit(ElementWiseVisitor{m_code}, accumulator, args[i]);
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