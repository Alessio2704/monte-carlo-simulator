#include <iostream>
#include <vector>
#include <memory>
#include <string>
#include <numeric>

#include "distributions/IDistribution.h"
#include "distributions/NormalDistribution.h"
#include "distributions/PertDistribution.h"
#include "distributions/UniformDistribution.h"
#include "distributions/LognormalDistribution.h"
#include "distributions/TriangularDistribution.h"
#include "distributions/BernoulliDistribution.h"
#include "distributions/BetaDistribution.h"

// Helper function remains the same
void runSimulation(IDistribution* dist, int num_samples, const std::string& dist_name) {
    std::cout << "\n--- Running Simulation for " << dist_name << " ---" << std::endl;
    std::vector<double> results;
    results.reserve(num_samples);

    for (int i = 0; i < num_samples; ++i) {
        results.push_back(dist->getSample());
    }

    double sum = std::accumulate(results.begin(), results.end(), 0.0);
    double mean = sum / results.size();

    std::cout << "Generated " << num_samples << " samples." << std::endl;
    std::cout << "Average value: " << mean << std::endl;
    std::cout << "First 5 samples: ";
    for(int i = 0; i < std::min((int)results.size(), 5); ++i) {
        std::cout << results[i] << " ";
    }
    std::cout << std::endl;
}

int main() {
    // Use a vector to hold our distributions. This is a clean way to manage them.
    // The vector stores unique_ptrs, ensuring memory is handled automatically.
    std::vector<std::pair<std::string, std::unique_ptr<IDistribution>>> distributions;

    // Add all our distributions to the list
    distributions.emplace_back("Revenue Growth (Normal)", std::make_unique<NormalDistribution>(100.0, 15.0));
    distributions.emplace_back("Operating Margin (PERT)", std::make_unique<PertDistribution>(0.15, 0.22, 0.28));
    distributions.emplace_back("Competitor Price (Uniform)", std::make_unique<UniformDistribution>(250.0, 300.0));
    distributions.emplace_back("Stock Price (Lognormal)", std::make_unique<LognormalDistribution>(5.0, 0.5));
    distributions.emplace_back("Cost Estimate (Triangular)", std::make_unique<TriangularDistribution>(1000.0, 1100.0, 1500.0));
    distributions.emplace_back("Contract Win (Bernoulli)", std::make_unique<BernoulliDistribution>(0.75)); // 75% chance of success
    distributions.emplace_back("Recovery Rate (Beta)", std::make_unique<BetaDistribution>(2.0, 5.0));
    
    // Loop through and run a simulation for each one
    for (const auto& pair : distributions) {
        runSimulation(pair.second.get(), 10000, pair.first);
    }

    return 0;
}