#include "distributions/NormalDistribution.h"
#include <iostream>

thread_local std::mt19937 NormalDistribution::m_generator(std::random_device{}());

NormalDistribution::NormalDistribution(double mean, double stddev): 
m_mean(mean), 
m_stddev(stddev),
 m_distribution(mean, stddev) {
    std::cout << "NormalDistribution created with mean " << m_mean << " and stddev " << m_stddev << std::endl;
}

double NormalDistribution::getSample() {
    return m_distribution(m_generator);
}