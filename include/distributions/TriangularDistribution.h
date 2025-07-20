#pragma once

#include "distributions/IDistribution.h"
#include <random>

class TriangularDistribution : public IDistribution {
public:
    TriangularDistribution(double min, double mostLikely, double max);
    double getSample() override;

private:
    double m_min;
    double m_mostLikely;
    double m_max;
    std::uniform_real_distribution<> m_uniform_dist;
    static thread_local std::mt19937 m_generator;
};