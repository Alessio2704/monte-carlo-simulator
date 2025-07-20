#pragma once

#include "distributions/IDistribution.h"
#include <random>

class UniformDistribution : public IDistribution {
public:
    UniformDistribution(double min, double max);
    double getSample() override;

private:
    double m_min;
    double m_max;
    std::uniform_real_distribution<> m_distribution;
    static thread_local std::mt19937 m_generator;
};