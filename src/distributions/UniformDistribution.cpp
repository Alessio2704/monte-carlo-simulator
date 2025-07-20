#include "distributions/UniformDistribution.h"
#include <iostream>

thread_local std::mt19937 UniformDistribution::m_generator(std::random_device{}());

UniformDistribution::UniformDistribution(double min, double max): 
    m_min(min),
    m_max(max),
    m_distribution(min, max) {
    std::cout << "UniformDistribution created with min=" << m_min << " and max=" << m_max << std::endl;
}

double UniformDistribution::getSample() {
    return m_distribution(m_generator);
}