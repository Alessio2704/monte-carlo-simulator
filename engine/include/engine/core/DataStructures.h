#pragma once

#include <string>
#include <vector>
#include <variant>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using TrialValue = std::variant<double, std::vector<double>, std::string, bool>;

enum class OpCode
{
    // Math
    ADD,
    MULTIPLY,
    SUBTRACT,
    DIVIDE,
    POWER,
    LOG,
    LOG10,
    EXP,
    SIN,
    COS,
    TAN,
    // Comparison
    EQ,
    NEQ,
    GT,
    LT,
    GTE,
    LTE,
    // Logical
    AND,
    OR,
    NOT,
    // Series
    GROW_SERIES,
    NPV,
    SUM_SERIES,
    GET_ELEMENT,
    SERIES_DELTA,
    COMPOUND_SERIES,
    COMPOSE_VECTOR,
    INTERPOLATE_SERIES,
    CAPITALIZE_EXPENSE,
    DELETE_ELEMENT,
    // Core
    IDENTITY // For variable-to-variable assignment
};