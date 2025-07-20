#pragma once

#include "engine/datastructures.h"
#include <string>
#include <vector>

class SimulationEngine
{
public:
    // Constructor takes the path to the JSON recipe file.
    explicit SimulationEngine(const std::string &json_recipe_path);

    // The main public method to run the simulation.
    std::vector<double> run();

private:
    // A private method to handle parsing the JSON file.
    void parse_recipe();

    // The recipe object that holds our entire simulation plan.
    SimulationRecipe m_recipe;

    // The path to the JSON file, stored for later use.
    std::string m_recipe_path;
};