#pragma once

#include "distributions/IDistribution.h"
#include <random>

class BernoulliDistribution : public IDistribution {
public:
    BernoulliDistribution(double p);
    double getSample() override;

private:
    std::bernoulli_distribution m_distribution;
    static thread_local std::mt19937 m_generator;
};