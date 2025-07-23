#include <gtest/gtest.h>
#include "distributions/NormalDistribution.h"
#include "distributions/PertDistribution.h"
#include "distributions/UniformDistribution.h"
#include "distributions/LognormalDistribution.h"
#include "distributions/TriangularDistribution.h"
#include "distributions/BernoulliDistribution.h"
#include "distributions/BetaDistribution.h"
#include <vector>
#include <numeric>
#include <cmath>

// --- Test Suite for Distribution Classes ---

// This test verifies the statistical properties of the NormalDistribution.
TEST(DistributionTests, NormalDistributionStats)
{
    NormalDistribution dist(100.0, 15.0); // Mean = 100, StdDev = 15
    int num_samples = 100000;
    std::vector<double> samples;
    samples.reserve(num_samples);
    for (int i = 0; i < num_samples; ++i)
    {
        samples.push_back(dist.getSample());
    }

    // Calculate the sample mean.
    double sum = std::accumulate(samples.begin(), samples.end(), 0.0);
    double mean = sum / num_samples;

    // Calculate the sample standard deviation.
    double sq_sum = 0.0;
    for (double x : samples)
    {
        sq_sum += (x - mean) * (x - mean);
    }
    double stddev = std::sqrt(sq_sum / num_samples);

    // Assert that the sample statistics are "close enough" to the theoretical values.
    // The tolerance (2.0 here) allows for natural randomness.
    EXPECT_NEAR(mean, 100.0, 2.0);
    EXPECT_NEAR(stddev, 15.0, 2.0);
}

// This test verifies the bounds and mean of the PertDistribution.
TEST(DistributionTests, PertDistributionStats)
{
    PertDistribution dist(50.0, 100.0, 200.0);                 // Min, Mode, Max
    double expected_mean = (50.0 + 4.0 * 100.0 + 200.0) / 6.0; // ~125.0

    int num_samples = 100000;
    std::vector<double> samples;
    double sum = 0.0;
    for (int i = 0; i < num_samples; ++i)
    {
        double s = dist.getSample();
        // Assert that every single sample is within the defined min/max bounds.
        ASSERT_GE(s, 50.0);  // Greater than or equal to min
        ASSERT_LE(s, 200.0); // Less than or equal to max
        sum += s;
    }

    double mean = sum / num_samples;
    EXPECT_NEAR(mean, expected_mean, 5.0); // Allow a wider tolerance for skewed distributions
}

// Test that the UniformDistribution stays within its bounds.
TEST(DistributionTests, UniformDistributionBounds)
{
    UniformDistribution dist(-10.0, 10.0);
    for (int i = 0; i < 10000; ++i)
    {
        double s = dist.getSample();
        ASSERT_GE(s, -10.0);
        ASSERT_LE(s, 10.0);
    }
}

TEST(DistributionTests, LognormalDistributionStats)
{
    // Note: The mean of a lognormal is NOT the log_mean parameter.
    // Mean = exp(log_mean + (log_stddev^2 / 2))
    double log_mean = 2.0;
    double log_stddev = 0.5;
    double expected_mean = std::exp(log_mean + (log_stddev * log_stddev) / 2.0);

    LognormalDistribution dist(log_mean, log_stddev);

    int num_samples = 100000;
    double sum = 0.0;
    for (int i = 0; i < num_samples; ++i)
    {
        double s = dist.getSample();
        // A key property of the lognormal distribution is that it cannot be negative.
        ASSERT_GE(s, 0.0);
        sum += s;
    }

    double mean = sum / num_samples;
    EXPECT_NEAR(mean, expected_mean, 0.5); // Tolerance can be wider for skewed distributions
}

TEST(DistributionTests, TriangularDistributionStats)
{
    // The mean of a triangular distribution is (min + mode + max) / 3
    double expected_mean = (10.0 + 20.0 + 60.0) / 3.0; // ~30.0

    TriangularDistribution dist(10.0, 20.0, 60.0);

    int num_samples = 100000;
    double sum = 0.0;
    for (int i = 0; i < num_samples; ++i)
    {
        double s = dist.getSample();
        ASSERT_GE(s, 10.0);
        ASSERT_LE(s, 60.0);
        sum += s;
    }

    double mean = sum / num_samples;
    EXPECT_NEAR(mean, expected_mean, 2.0);
}

TEST(DistributionTests, BernoulliDistributionStats)
{
    // The mean of a Bernoulli distribution is simply p, the probability of success.
    double p = 0.75;
    BernoulliDistribution dist(p);

    int num_samples = 100000;
    double successes = 0.0;
    for (int i = 0; i < num_samples; ++i)
    {
        double s = dist.getSample();
        // Assert that the result is ONLY 0.0 or 1.0
        ASSERT_TRUE(s == 0.0 || s == 1.0);
        if (s == 1.0)
        {
            successes++;
        }
    }

    double mean = successes / num_samples;
    EXPECT_NEAR(mean, p, 0.01); // With many samples, the mean should be very close to p.
}

TEST(DistributionTests, BetaDistributionStats)
{
    // The mean of a Beta distribution is alpha / (alpha + beta)
    double alpha = 2.0;
    double beta = 5.0;
    double expected_mean = alpha / (alpha + beta); // ~0.2857

    BetaDistribution dist(alpha, beta);

    int num_samples = 100000;
    std::vector<double> samples;
    samples.reserve(num_samples);
    double sum = 0.0;
    for (int i = 0; i < num_samples; ++i)
    {
        double s = dist.getSample();
        // A key property of the beta distribution is that it's always between 0 and 1.
        ASSERT_GE(s, 0.0);
        ASSERT_LE(s, 1.0);
        sum += s;
    }

    double mean = sum / num_samples;
    EXPECT_NEAR(mean, expected_mean, 0.01);
}