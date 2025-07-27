// test/engine_tests.cpp

#include <gtest/gtest.h>
#include <fstream>
#include <string>
#include <vector>
#include <tuple>
#include <numeric>
#include <cmath>
#include "engine/SimulationEngine.h"

// Helper function to create a test recipe file.
void create_test_recipe(const std::string &filename, const std::string &content)
{
    std::ofstream test_file(filename);
    test_file << content;
    test_file.close();
}

// --- Parameterized Test Fixture for Deterministic Operations ---
using TestParam = std::tuple<std::string, TrialValue, bool>;

class DeterministicEngineTest : public ::testing::TestWithParam<TestParam>
{
};

TEST_P(DeterministicEngineTest, ExecutesCorrectly)
{
    const auto params = GetParam();
    const std::string &recipe_content = std::get<0>(params);
    const TrialValue &expected_result = std::get<1>(params);
    const bool is_vector_output = std::get<2>(params);
    const std::string filename = "param_test.json";
    create_test_recipe(filename, recipe_content);

    SimulationEngine engine(filename);
    std::vector<TrialValue> results = engine.run();
    ASSERT_EQ(results.size(), 1);

    // Use a slightly larger tolerance for complex calcs like capitalize_expense
    const double tolerance = 1e-6;
    if (is_vector_output)
    {
        ASSERT_TRUE(std::holds_alternative<std::vector<double>>(results[0]));
        const auto &result_vec = std::get<std::vector<double>>(results[0]);
        const auto &expected_vec = std::get<std::vector<double>>(expected_result);
        ASSERT_EQ(result_vec.size(), expected_vec.size());
        for (size_t i = 0; i < result_vec.size(); ++i)
        {
            EXPECT_NEAR(result_vec[i], expected_vec[i], tolerance);
        }
    }
    else
    {
        ASSERT_TRUE(std::holds_alternative<double>(results[0]));
        double final_value = std::get<double>(results[0]);
        double expected_value = std::get<double>(expected_result);
        EXPECT_NEAR(final_value, expected_value, tolerance);
    }
}

// --- Test Suites for Deterministic Operations ---

// --- Basic Assignment Tests ---
INSTANTIATE_TEST_SUITE_P(
    AssignmentTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","execution_steps":[{"type":"literal_assignment","result":"A","value":123.45}]})", TrialValue(123.45), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","execution_steps":[{"type":"literal_assignment","result":"A","value":[1.0,2.0,3.0]}]})", TrialValue(std::vector<double>{1.0, 2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","execution_steps":[{"type":"literal_assignment","result":"A","value":99.0},{"type":"execution_assignment","result":"B","function":"identity","args":["A"]}]})", TrialValue(99.0), false)));

// --- Binary and Unary Math Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    MathOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})", TrialValue(30.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"execution_assignment","result":"C","function":"subtract","args":["A","B"]}]})", TrialValue(-10.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"execution_assignment","result":"C","function":"multiply","args":["A","B"]}]})", TrialValue(200.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":20},{"type":"literal_assignment","result":"B","value":10},{"type":"execution_assignment","result":"C","function":"divide","args":["A","B"]}]})", TrialValue(2.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":2},{"type":"literal_assignment","result":"B","value":8},{"type":"execution_assignment","result":"C","function":"power","args":["A","B"]}]})", TrialValue(256.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","execution_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"execution_assignment","result":"B","function":"log","args":["A"]}]})", TrialValue(std::log(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","execution_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"execution_assignment","result":"B","function":"log10","args":["A"]}]})", TrialValue(std::log10(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","execution_steps":[{"type":"literal_assignment","result":"A","value":2},{"type":"execution_assignment","result":"B","function":"exp","args":["A"]}]})", TrialValue(std::exp(2.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","execution_steps":[{"type":"literal_assignment","result":"A","value":0},{"type":"execution_assignment","result":"B","function":"sin","args":["A"]}]})", TrialValue(std::sin(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","execution_steps":[{"type":"literal_assignment","result":"A","value":0},{"type":"execution_assignment","result":"B","function":"cos","args":["A"]}]})", TrialValue(std::cos(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","execution_steps":[{"type":"literal_assignment","result":"A","value":0},{"type":"execution_assignment","result":"B","function":"tan","args":["A"]}]})", TrialValue(std::tan(0.0)), false)));

// --- Vector and Time-Series Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    VectorOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[1,2,3]},{"type":"literal_assignment","result":"B","value":[4,5,6]},{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})", TrialValue(std::vector<double>{5.0, 7.0, 9.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"base","value":100},{"type":"literal_assignment","result":"rate","value":0.1},{"type":"execution_assignment","result":"C","function":"grow_series","args":["base","rate",3]}]})", TrialValue(std::vector<double>{110.0, 121.0, 133.1}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"base","value":100},{"type":"literal_assignment","result":"rates","value":[0.1,0.2]},{"type":"execution_assignment","result":"C","function":"compound_series","args":["base","rates"]}]})", TrialValue(std::vector<double>{110.0, 132.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"series","value":[100,110,125]},{"type":"execution_assignment","result":"C","function":"series_delta","args":["series"]}]})", TrialValue(std::vector<double>{0.0, 10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"series","value":[10,20,70]},{"type":"execution_assignment","result":"C","function":"sum_series","args":["series"]}]})", TrialValue(100.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"start","value":10},{"type":"literal_assignment","result":"end","value":50},{"type":"execution_assignment","result":"C","function":"interpolate_series","args":["start","end",5]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0, 40.0, 50.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"literal_assignment","result":"C_in","value":30},{"type":"execution_assignment","result":"C","function":"compose_vector","args":["A","B","C_in"]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"current_rd","value":100.0},{"type":"literal_assignment","result":"past_rd","value":[90.0,80.0,70.0]},{"type":"literal_assignment","result":"period","value":3.0},{"type":"execution_assignment","result":"C","function":"capitalize_expense","args":["current_rd","past_rd","period"]}]})", TrialValue(std::vector<double>{186.66666666666666, 80.0}), true)));

// --- Nested Expression Test ---
INSTANTIATE_TEST_SUITE_P(
    NestedExpressionTest,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"D","execution_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"literal_assignment","result":"C","value":5},{"type":"execution_assignment","result":"D","function":"multiply","args":["A",{"function":"subtract","args":["B","C"]}]}]})", TrialValue(150.0), false)));

// --- NEW: Mixed-Type Vector Math Tests ---
INSTANTIATE_TEST_SUITE_P(
    MixedTypeVectorMathTests,
    DeterministicEngineTest,
    ::testing::Values(
        // Add
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[10,20,30]},{"type":"execution_assignment","result":"C","function":"add","args":["A",5.0]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[10,20,30]},{"type":"execution_assignment","result":"C","function":"add","args":[5.0,"A"]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        // Subtract
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[10,20]},{"type":"execution_assignment","result":"C","function":"subtract","args":["A",3.0]}]})", TrialValue(std::vector<double>{7.0, 17.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[10,20]},{"type":"execution_assignment","result":"C","function":"subtract","args":[100.0,"A"]}]})", TrialValue(std::vector<double>{90.0, 80.0}), true),
        // Multiply
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[2,4,6]},{"type":"execution_assignment","result":"C","function":"multiply","args":["A",10.0]}]})", TrialValue(std::vector<double>{20.0, 40.0, 60.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[10,20,30]},{"type":"execution_assignment","result":"C","function":"multiply","args":[0.5,"A"]}]})", TrialValue(std::vector<double>{5.0, 10.0, 15.0}), true),
        // Divide
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[100,200]},{"type":"execution_assignment","result":"C","function":"divide","args":["A",10.0]}]})", TrialValue(std::vector<double>{10.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[2,4,5]},{"type":"execution_assignment","result":"C","function":"divide","args":[100.0,"A"]}]})", TrialValue(std::vector<double>{50.0, 25.0, 20.0}), true),
        // Power
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[2,3,4]},{"type":"execution_assignment","result":"C","function":"power","args":["A",2.0]}]})", TrialValue(std::vector<double>{4.0, 9.0, 16.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[1,2,3]},{"type":"execution_assignment","result":"C","function":"power","args":[2.0,"A"]}]})", TrialValue(std::vector<double>{2.0, 4.0, 8.0}), true)));

// =============================================================================
// --- STATISTICAL TESTS FOR SAMPLERS ---
// =============================================================================
class EngineSamplerTest : public ::testing::Test
{
protected:
    void RunAndAnalyze(const std::string &recipe_content, int num_trials, double expected_mean, double tolerance, bool check_bounds = false, double min_bound = 0.0, double max_bound = 0.0)
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
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Normal","args":[100.0,15.0]}]})", 20000, 100.0, 0.5);
}

TEST_F(EngineSamplerTest, Pert)
{
    double expected_mean = (50.0 + 4.0 * 100.0 + 200.0) / 6.0; // ~125
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Pert","args":[50,100,200]}]})", 20000, expected_mean, 2.0, true, 50.0, 200.0);
}

TEST_F(EngineSamplerTest, Uniform)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Uniform","args":[-10,10]}]})", 20000, 0.0, 0.5, true, -10.0, 10.0);
}

TEST_F(EngineSamplerTest, Triangular)
{
    double expected_mean = (10.0 + 20.0 + 60.0) / 3.0; // ~30.0
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Triangular","args":[10,20,60]}]})", 20000, expected_mean, 1.0, true, 10.0, 60.0);
}

TEST_F(EngineSamplerTest, Bernoulli)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Bernoulli","args":[0.75]}]})", 20000, 0.75, 0.01, true, 0.0, 1.0);
}

TEST_F(EngineSamplerTest, Beta)
{
    double expected_mean = 2.0 / (2.0 + 5.0); // ~0.2857
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Beta","args":[2.0, 5.0]}]})", 20000, expected_mean, 0.01, true, 0.0, 1.0);
}

TEST_F(EngineSamplerTest, Lognormal)
{
    double log_mean = 2.0, log_stddev = 0.5;
    double expected_mean = std::exp(log_mean + (log_stddev * log_stddev) / 2.0); // ~8.37
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Lognormal","args":[2.0,0.5]}]})", 20000, expected_mean, 0.5, true, 0.0, 1e9);
}

// =============================================================================
// --- ERROR HANDLING AND EDGE CASE TESTS ---
// =============================================================================
TEST(EngineErrorTests, ThrowsOnUndefinedVariable)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST(EngineErrorTests, ThrowsOnDivisionByZero)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":100},{"type":"literal_assignment","result":"B","value":0},{"type":"execution_assignment","result":"C","function":"divide","args":["A","B"]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST(EngineErrorTests, ThrowsOnVectorSizeMismatch)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[1,2]},{"type":"literal_assignment","result":"B","value":[1,2,3]},{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST(EngineErrorTests, ThrowsOnIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","execution_steps":[{"type":"literal_assignment","result":"A","value":[10,20]},{"type":"execution_assignment","result":"C","function":"get_element","args":["A",5]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST(EngineErrorTests, ThrowsOnInvalidPertParams)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"X","execution_steps":[{"type":"execution_assignment","result":"X","function":"Pert","args":[100,50,200]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::invalid_argument);
}