#include "include/engine/io.h"
#include "include/engine/datastructures.h"
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <variant>

void write_results_to_csv(const std::string &path, const std::vector<TrialValue> &results)
{
    if (results.empty())
        return;

    std::ofstream output_file(path);
    if (!output_file.is_open())
    {
        std::cerr << "Warning: Could not open output file '" << path << "' for writing." << std::endl;
        return;
    }

    std::cout << "\n--- Writing results to " << path << " ---" << std::endl;

    // Use a visitor on the first element to determine the header and structure
    std::visit(
        [&](auto &&first_result)
        {
            using T = std::decay_t<decltype(first_result)>;

            // Case 1: The result is a SCALAR (double)
            if constexpr (std::is_same_v<T, double>)
            {
                output_file << "Result\n"; // Write header
                for (const auto &res : results)
                {
                    output_file << std::get<double>(res) << "\n";
                }
            }
            // Case 2: The result is a VECTOR (vector<double>)
            else if constexpr (std::is_same_v<T, std::vector<double>>)
            {
                if (first_result.empty())
                    return;
                // Write header: Period_1,Period_2,...
                for (size_t i = 0; i < first_result.size(); ++i)
                {
                    output_file << "Period_" << i + 1 << (i == first_result.size() - 1 ? "" : ",");
                }
                output_file << "\n";

                // Write data rows
                for (const auto &res : results)
                {
                    const auto &vec = std::get<std::vector<double>>(res);
                    // A safety check to handle inconsistent vector sizes gracefully
                    if (vec.size() != first_result.size())
                        continue;
                    for (size_t i = 0; i < vec.size(); ++i)
                    {
                        output_file << vec[i] << (i == vec.size() - 1 ? "" : ",");
                    }
                    output_file << "\n";
                }
            }
        },
        results[0]);

    std::cout << "Successfully wrote " << results.size() << " trials." << std::endl;
}