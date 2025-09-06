#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <variant>
#include <nlohmann/json.hpp>

using json = nlohmann::json;
using TrialValue = std::variant<double, std::vector<double>, std::string>;

enum class OpCode
{
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
    GROW_SERIES,
    NPV,
    SUM_SERIES,
    GET_ELEMENT,
    SERIES_DELTA,
    COMPOUND_SERIES,
    COMPOSE_VECTOR,
    INTERPOLATE_SERIES,
    CAPITALIZE_EXPENSE,
    IDENTITY // For variable-to-variable assignment
};