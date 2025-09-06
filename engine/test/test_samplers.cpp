#include "test_helpers.h"

class EngineSamplerTest : public FileCleanupTest
{
protected:
    void RunAndAnalyze(const std::string &recipe_content, size_t num_trials, double expected_mean, double tolerance, bool check_bounds = false, double min_bound = 0.0, double max_bound = 0.0)
    {
        const std::string filename = "sampler_test.json";
        create_test_recipe(filename, recipe_content);
        SimulationEngine engine(filename);
        std::vector<TrialValue> results = engine.run();

        ASSERT_EQ(results.size(), num_trials);

        std::vector<double> samples;
        samples.reserve(results.size());
        for (const auto &res : results)
        {
            double sample = std::get<double>(res);
            samples.push_back(sample);
            if (check_bounds)
            {
                ASSERT_GE(sample, min_bound);
                ASSERT_LE(sample, max_bound);
            }
        }

        double sum = std::accumulate(samples.begin(), samples.end(), 0.0);
        double mean = sum / samples.size();
        EXPECT_NEAR(mean, expected_mean, tolerance);
    }
};

TEST_F(EngineSamplerTest, Normal)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Normal","args":[100.0,15.0]}]})", 20000, 100.0, 0.5);
}

TEST_F(EngineSamplerTest, Pert)
{
    double expected_mean = (50.0 + 4.0 * 100.0 + 200.0) / 6.0; // ~125
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Pert","args":[50,100,200]}]})", 20000, expected_mean, 2.0, true, 50.0, 200.0);
}

TEST_F(EngineSamplerTest, Uniform)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Uniform","args":[-10,10]}]})", 20000, 0.0, 0.5, true, -10.0, 10.0);
}

TEST_F(EngineSamplerTest, Triangular)
{
    double expected_mean = (10.0 + 20.0 + 60.0) / 3.0; // ~30.0
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Triangular","args":[10,20,60]}]})", 20000, expected_mean, 1.0, true, 10.0, 60.0);
}

TEST_F(EngineSamplerTest, Bernoulli)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Bernoulli","args":[0.75]}]})", 20000, 0.75, 0.01, true, 0.0, 1.0);
}

TEST_F(EngineSamplerTest, Beta)
{
    double expected_mean = 2.0 / (2.0 + 5.0); // ~0.2857
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Beta","args":[2.0, 5.0]}]})", 20000, expected_mean, 0.01, true, 0.0, 1.0);
}

TEST_F(EngineSamplerTest, Lognormal)
{
    double log_mean = 2.0, log_stddev = 0.5;
    double expected_mean = std::exp(log_mean + (log_stddev * log_stddev) / 2.0); // ~8.37
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Lognormal","args":[2.0,0.5]}]})", 20000, expected_mean, 0.5, true, 0.0, 1e9);
}