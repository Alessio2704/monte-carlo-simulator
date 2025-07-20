#include "distributions/BetaDistribution.h"
#include <iostream>
#include <stdexcept>

thread_local std::mt19937 BetaDistribution::m_generator(std::random_device{}());

BetaDistribution::BetaDistribution(double alpha, double beta):
    m_alpha(alpha),
    m_beta(beta),
    m_gammaDist1(alpha, 1.0),
    m_gammaDist2(beta, 1.0) {

    if (alpha <= 0 || beta <= 0) {
        throw std::invalid_argument("Beta distribution parameters (alpha, beta) must be positive.");
    }
    
    std::cout << "BetaDistribution created with alpha=" << m_alpha << " and beta=" << m_beta << std::endl;
}

double BetaDistribution::getSample() {
    double gamma1 = m_gammaDist1(m_generator);
    double gamma2 = m_gammaDist2(m_generator);

    if (gamma1 + gamma2 == 0.0) {
        return 0.0;
    }
    return gamma1 / (gamma1 + gamma2);
}