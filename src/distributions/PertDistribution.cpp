#include "distributions/PertDistribution.h"
#include <iostream>
#include <stdexcept>

PertDistribution::PertDistribution(double min, double mostLikely, double max): m_min(min), m_max(max) {

    if (min > mostLikely || mostLikely > max || min == max) {
        throw std::invalid_argument("Invalid PERT parameters: must be min <= mostLikely <= max and min != max.");
    }

    const double gamma = 4.0;
    double alpha = 1.0 + gamma * (mostLikely - m_min) / (max - m_min);
    double beta = 1.0 + gamma * (max - mostLikely) / (max - min);

    m_beta = std::make_unique<BetaDistribution>(alpha, beta);

    std::cout << "PertDistribution created with min=" << m_min << ", mode=" << mostLikely << ", max=" << m_max << std::endl;
}

double PertDistribution::getSample() {
    double betaSample = m_beta->getSample();
    return m_min + betaSample * (m_max - m_min);
}