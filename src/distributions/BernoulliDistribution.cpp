#include "distributions/BernoulliDistribution.h"
#include <iostream>

thread_local std::mt19937 BernoulliDistribution::m_generator(std::random_device{}());

BernoulliDistribution::BernoulliDistribution(double p): m_distribution(p) {
std::cout << "BernoulliDistribution created with p=" << p << std::endl;
}

double BernoulliDistribution::getSample() {
return static_cast<double>(m_distribution(m_generator));
}