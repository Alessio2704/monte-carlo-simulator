#include "include/engine/SimulationEngine.h"
#include "include/engine/io.h"
#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <variant>
#include <fstream>

void print_statistics(const std::vector<TrialValue> &results)
{
    if (results.empty())
    {
        std::cout << "No simulation data to analyze." << std::endl;
        return;
    }

    // Use a visitor to handle either a scalar (double) or vector result type
    std::visit([&](auto &&first_result)
               {
        using T = std::decay_t<decltype(first_result)>;
        if constexpr (std::is_same_v<T, double>) {
            std::cout << "\n--- SCALAR Simulation Statistics ---" << std::endl;
            std::vector<double> scalar_data;
            scalar_data.reserve(results.size());
            for(const auto& res : results) {
                scalar_data.push_back(std::get<double>(res));
            }

            double sum = std::accumulate(scalar_data.begin(), scalar_data.end(), 0.0);
            double mean = sum / scalar_data.size();
            double sum_of_squares = 0.0;
            for (double val : scalar_data) {
                sum_of_squares += (val - mean) * (val - mean);
            }
            double stddev = std::sqrt(sum_of_squares / scalar_data.size());
            double min_value = *std::min_element(scalar_data.begin(), scalar_data.end());
            double max_value = *std::max_element(scalar_data.begin(), scalar_data.end());

            std::cout << "Trials:     " << scalar_data.size() << std::endl;
            std::cout << "Mean:       " << mean << std::endl;
            std::cout << "Std. Dev:   " << stddev << std::endl;
            std::cout << "Min Value:  " << min_value << std::endl;
            std::cout << "Max Value:  " << max_value << std::endl;
        }
        else if constexpr (std::is_same_v<T, std::vector<double>>) {
            std::cout << "\n--- VECTOR Simulation Statistics ---" << std::endl;
            if (first_result.empty()) {
                std::cout << "Result vectors are empty." << std::endl;
                return;
            }
            size_t num_periods = first_result.size();
            std::vector<double> mean_vector(num_periods, 0.0);
            std::vector<double> stddev_vector(num_periods, 0.0);

            for (const auto& res_variant : results) {
                const auto& vec = std::get<std::vector<double>>(res_variant);
                if (vec.size() != num_periods) {
                    std::cerr << "Warning: Inconsistent vector sizes in results. Skipping." << std::endl;
                    continue;
                }
                for (size_t i = 0; i < num_periods; ++i) {
                    mean_vector[i] += vec[i];
                }
            }
            for (size_t i = 0; i < num_periods; ++i) {
                mean_vector[i] /= results.size();
            }

            for (const auto& res_variant : results) {
                const auto& vec = std::get<std::vector<double>>(res_variant);
                 if (vec.size() != num_periods) continue;
                for (size_t i = 0; i < num_periods; ++i) {
                    stddev_vector[i] += (vec[i] - mean_vector[i]) * (vec[i] - mean_vector[i]);
                }
            }
            for (size_t i = 0; i < num_periods; ++i) {
                stddev_vector[i] = std::sqrt(stddev_vector[i] / results.size());
            }

            std::cout << "Trials: " << results.size() << ", Periods per trial: " << num_periods << std::endl;
            for (size_t i = 0; i < num_periods; ++i) {
                std::cout << "  Period " << i + 1 << ": Mean = " << mean_vector[i] 
                          << ", Std. Dev = " << stddev_vector[i] << std::endl;
            }
        } }, results[0]);
}

int main(int argc, char *argv[])
{
    if (argc != 2)
    {
        std::cerr << "Usage: " << argv[0] << " <path_to_recipe.json>" << std::endl;
        return 1;
    }

    std::string recipe_path = argv[1];

    try
    {
        SimulationEngine engine(recipe_path);
        std::vector<TrialValue> results = engine.run();
        print_statistics(results);

        // Check if an output file is specified and write to it
        std::string output_path = engine.get_output_file_path();

        if (!output_path.empty())
        {
            write_results_to_csv(output_path, results);
        }

        std::cout << "\nExecution finished." << std::endl;
    }
    catch (const std::exception &e)
    {
        std::cerr << "An error occurred: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}