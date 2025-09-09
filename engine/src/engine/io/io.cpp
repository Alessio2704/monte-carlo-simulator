#include "include/engine/io/io.h"
#include "include/engine/core/DataStructures.h"
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

    std::visit(
        [&](auto &&first_result)
        {
            using T = std::decay_t<decltype(first_result)>;

            if constexpr (std::is_same_v<T, double>)
            {
                output_file << "Result\n";
                for (const auto &res : results)
                {
                    output_file << std::get<double>(res) << "\n";
                }
            }
            else if constexpr (std::is_same_v<T, bool>)
            {
                output_file << "Result\n";
                for (const auto &res : results)
                {
                    output_file << (std::get<bool>(res) ? "true" : "false") << "\n";
                }
            }
            else if constexpr (std::is_same_v<T, std::vector<double>>)
            {
                if (first_result.empty())
                    return;
                for (size_t i = 0; i < first_result.size(); ++i)
                {
                    output_file << "Period_" << i + 1 << (i == first_result.size() - 1 ? "" : ",");
                }
                output_file << "\n";
                for (const auto &res : results)
                {
                    const auto &vec = std::get<std::vector<double>>(res);
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