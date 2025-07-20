#pragma once

#include "distributions/IDistribution.h"
#include <random>

class BetaDistribution : public IDistribution {
public:
    BetaDistribution(double alpha, double beta);
    double getSample() override;

private:
    double m_alpha;
    double m_beta;

    std::gamma_distribution<> m_gammaDist1;
    std::gamma_distribution<> m_gammaDist2;
    static thread_local std::mt19937 m_generator;
};