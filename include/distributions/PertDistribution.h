#pragma once

#include "distributions/IDistribution.h"
#include "distributions/BetaDistribution.h"
#include <memory>

class PertDistribution : public IDistribution {
public:
    PertDistribution(double min, double mostLikely, double max);
    double getSample() override;

private:
    double m_min;
    double m_max;
    std::unique_ptr<BetaDistribution> m_beta;
};