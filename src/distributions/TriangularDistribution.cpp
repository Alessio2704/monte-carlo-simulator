#include "distributions/TriangularDistribution.h"
#include <iostream>
#include <cmath> // For std::sqrt
#include <stdexcept>

thread_local std::mt19937 TriangularDistribution::m_generator(std::random_device{}());

TriangularDistribution::TriangularDistribution(double min, double mostLikely, double max)
    : m_min(min),
      m_mostLikely(mostLikely),
      m_max(max),
      m_uniform_dist(0.0, 1.0) {

    if (min > mostLikely || mostLikely > max) {
        throw std::invalid_argument("Invalid Triangular parameters: must be min <= mostLikely <= max.");
    }

    std::cout << "TriangularDistribution created with min=" << m_min << ", mode=" << m_mostLikely << ", max=" << m_max << std::endl;
}

double TriangularDistribution::getSample() {
    double u = m_uniform_dist(m_generator);

    double fc = (m_mostLikely - m_min) / (m_max - m_min);

    if (u < fc) {
        return m_min + std::sqrt(u * (m_max - m_min) * (m_mostLikely - m_min));
    } else {
        return m_max - std::sqrt((1 - u) * (m_max - m_min) * (m_max - m_mostLikely));
    }
}