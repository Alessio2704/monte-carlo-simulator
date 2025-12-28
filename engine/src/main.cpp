#include "include/engine/core/SimulationEngine.h"
#include "include/engine/io/io.h"
#include "include/engine/core/EngineException.h"
#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <variant>
#include <fstream>
#include <iomanip>

void print_statistics(const std::vector<TrialValue> &results);

struct TrialValueToJsonVisitor
{
    nlohmann::json operator()(double d) const { return d; }
    nlohmann::json operator()(const std::vector<double> &v) const { return v; }
    nlohmann::json operator()(const std::string &s) const { return s; }
    nlohmann::json operator()(bool b) const { return b; }
};

void run_preview_mode(const std::string &recipe_path)
{
    SimulationEngine engine(recipe_path, true);
    std::vector<TrialValue> results = engine.run();

    if (results.empty())
    {
        nlohmann::json error_json;
        error_json["status"] = "error";
        error_json["message"] = "No results were generated.";
        std::cout << error_json.dump() << std::endl;
        return;
    }

    nlohmann::json output_json;
    output_json["status"] = "success";

    std::visit(
        [&](auto &&first_result)
        {
            using T = std::decay_t<decltype(first_result)>;
            if constexpr (std::is_same_v<T, double>)
            {
                output_json["type"] = "scalar";
                double sum = 0.0;
                for (const auto &res : results)
                {
                    sum += std::get<double>(res);
                }
                output_json["value"] = std::round((sum / results.size()) * 10000.0) / 10000.0;
            }
            else if constexpr (std::is_same_v<T, std::vector<double>>)
            {
                output_json["type"] = "vector";
                const auto &original_vec = std::get<std::vector<double>>(results[0]);
                std::vector<double> rounded_vec;
                rounded_vec.reserve(original_vec.size());
                for (const auto &val : original_vec)
                {
                    rounded_vec.push_back(std::round(val * 10000.0) / 10000.0);
                }
                output_json["value"] = rounded_vec;
            }
            else if constexpr (std::is_same_v<T, bool>)
            {
                output_json["type"] = "boolean";
                output_json["value"] = std::get<bool>(results[0]);
            }
            else if constexpr (std::is_same_v<T, std::string>)
            {
                output_json["type"] = "string";
                output_json["value"] = std::get<std::string>(results[0]);
            }
        },
        results[0]);

    std::cout << output_json.dump() << std::endl;
}

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        std::cerr << "Usage: " << argv[0] << " [--preview] <path_to_recipe.json>" << std::endl;
        return 1;
    }

    std::string recipe_path;
    bool preview_mode = false;

    if (argc == 3 && std::string(argv[1]) == "--preview")
    {
        preview_mode = true;
        recipe_path = argv[2];
    }
    else if (argc == 2)
    {
        recipe_path = argv[1];
    }
    else
    {
        std::cerr << "Usage: " << argv[0] << " [--preview] <path_to_recipe.json>" << std::endl;
        return 1;
    }

    try
    {
        if (preview_mode)
        {
            run_preview_mode(recipe_path);
        }
        else
        {
            SimulationEngine engine(recipe_path);
            std::vector<TrialValue> results = engine.run();
            print_statistics(results);

            std::string output_path = engine.get_output_file_path();
            if (!output_path.empty())
            {
                write_results_to_csv(output_path, results);
            }
            std::cout << "\nExecution finished." << std::endl;
        }
    }
    catch (const EngineException &e)
    {
        if (preview_mode)
        {
            nlohmann::json error_json;
            error_json["status"] = "error";
            error_json["message"] = e.what();
            std::cout << error_json.dump() << std::endl;
        }
        else
        {
            std::cerr << "An error occurred: " << e.what() << std::endl;
        }
        return 1;
    }
    catch (const std::exception &e)
    {
        if (preview_mode)
        {
            nlohmann::json error_json;
            error_json["status"] = "error";
            error_json["message"] = e.what();
            std::cout << error_json.dump() << std::endl;
        }
        else
        {
            std::cerr << "An unexpected error occurred: " << e.what() << std::endl;
        }
        return 1;
    }

    return 0;
}

void print_statistics(const std::vector<TrialValue> &results)
{
    if (results.empty())
    {
        std::cout << "No simulation data to analyze." << std::endl;
        return;
    }

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