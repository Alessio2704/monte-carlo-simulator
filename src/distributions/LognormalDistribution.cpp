#include "distributions/LognormalDistribution.h"
#include <iostream>

thread_local std::mt19937 LognormalDistribution::m_generator(std::random_device{}());

LognormalDistribution::LognormalDistribution(double log_mean, double log_stddev): m_distribution(log_mean, log_stddev) {
std::cout << "LognormalDistribution created with log_mean=" << log_mean << " and log_stddev=" << log_stddev << std::endl;
}

double LognormalDistribution::getSample() {
return m_distribution(m_generator);
}