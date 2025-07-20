#pragma once

#include "distributions/IDistribution.h"
#include <random> 

class NormalDistribution : public IDistribution {
public:
    NormalDistribution(double mean, double stddev);
    double getSample() override;

private:
    double m_mean;
    double m_stddev;
    std::normal_distribution<> m_distribution;
    static thread_local std::mt19937 m_generator;
};