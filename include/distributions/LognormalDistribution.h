#pragma once

#include "distributions/IDistribution.h"
#include <random>

class LognormalDistribution : public IDistribution {
public:
    LognormalDistribution(double log_mean, double log_stddev);
    double getSample() override;

private:
    std::lognormal_distribution<> m_distribution;
    static thread_local std::mt19937 m_generator;
};