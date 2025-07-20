#include "engine/SimulationEngine.h"
#include <iostream>
#include <vector>
#include <numeric>   // Required for std::accumulate
#include <algorithm> // Required for std::min_element and std::max_element
#include <cmath>     // Required for std::sqrt

// A helper function to compute and display statistics for a vector of data.
void print_statistics(const std::vector<double> &data)
{
    if (data.empty())
    {
        std::cout << "No simulation data to analyze." << std::endl;
        return;
    }

    // --- Calculate Mean ---
    // std::accumulate sums up all elements in the vector.
    double sum = std::accumulate(data.begin(), data.end(), 0.0);
    double mean = sum / data.size();

    // --- Calculate Standard Deviation ---
    // This requires a second pass to sum the squared differences from the mean.
    double sum_of_squares = 0.0;
    for (const double val : data)
    {
        sum_of_squares += (val - mean) * (val - mean);
    }
    // The standard deviation is the square root of the variance.
    double stddev = std::sqrt(sum_of_squares / data.size());

    // --- Find Min/Max Range ---
    // std::min_element returns an "iterator" to the smallest element.
    // We use the '*' operator to "dereference" it and get the actual value.
    double min_value = *std::min_element(data.begin(), data.end());
    double max_value = *std::max_element(data.begin(), data.end());

    // --- Display Results ---
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
        // Create the engine, passing the path to our recipe.
        SimulationEngine engine("recipe.json");

        // Run the simulation and store the results.
        std::vector<double> results = engine.run();

        // Pass the results to our new helper function to be analyzed.
        print_statistics(results);

        std::cout << "\nMVP main execution finished." << std::endl;
    }
    catch (const std::exception &e)
    {
        // If anything goes wrong (file not found, JSON parse error, etc.),
        // we will catch the exception and print a friendly error message.
        std::cerr << "An error occurred: " << e.what() << std::endl;
        return 1; // Return a non-zero value to indicate failure.
    }
    return 0; // Success.
}