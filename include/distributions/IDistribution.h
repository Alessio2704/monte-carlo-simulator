#pragma once

class IDistribution {
public:
    virtual ~IDistribution() = default;
    virtual double getSample() = 0;
};