#pragma once

#include "engine/datastructures.h"
#include <string>
#include <vector>

class SimulationEngine
{
public:
    explicit SimulationEngine(const std::string &json_recipe_path);
    std::vector<double> run();

private:
    void parse_recipe();
    double get_value(const std::string &arg, const std::unordered_map<std::string, double> &context);
    SimulationRecipe m_recipe;
    std::string m_recipe_path;
};