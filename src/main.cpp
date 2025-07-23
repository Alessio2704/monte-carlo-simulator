#include "engine/SimulationEngine.h"
#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

void print_statistics(const std::vector<double> &data)
{
    if (data.empty())
    {
        std::cout << "No simulation data to analyze." << std::endl;
        return;
    }

    double sum = std::accumulate(data.begin(), data.end(), 0.0);
    double mean = sum / data.size();

    double sum_of_squares = 0.0;

    for (const double val : data)
    {
        sum_of_squares += (val - mean) * (val - mean);
    }

    double stddev = std::sqrt(sum_of_squares / data.size());

    double min_value = *std::min_element(data.begin(), data.end());
    double max_value = *std::max_element(data.begin(), data.end());

    std::cout << "\n--- Simulation Statistics ---" << std::endl;
    std::cout << "Trials:     " << data.size() << std::endl;
    std::cout << "Mean:       " << mean << std::endl;
    std::cout << "Std. Dev:   " << stddev << std::endl;
    std::cout << "Min Value:  " << min_value << std::endl;
    std::cout << "Max Value:  " << max_value << std::endl;
}

int main()
{
    try
    {
        SimulationEngine engine("compound_series_test_direct_array.json");

        std::vector<double> results = engine.run();

        print_statistics(results);

        std::cout << "\nMVP main execution finished." << std::endl;
    }
    catch (const std::exception &e)
    {
        std::cerr << "An error occurred: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}