#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <fstream>
#include <string>
#include <vector>
#include <tuple>
#include <numeric>
#include <cmath>
#include <cstdio>

#include "include/engine/core/SimulationEngine.h"
#include "include/engine/io/io.h"

// Helper function to create a test recipe file.
void create_test_recipe(const std::string &filename, const std::string &content)
{
    std::ofstream test_file(filename);
    test_file << content;
    test_file.close();
}

// Helper to read a file's content into a string
std::string read_file_content(const std::string &path)
{
    std::ifstream file(path);
    if (!file.is_open())
    {
        return "ERROR: FILE_NOT_FOUND";
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

// Executes a command and captures its standard output.
std::string exec_command(const char *cmd)
{
    std::array<char, 128> buffer;
    std::string result;

#ifdef _WIN32
    // Use the Windows-specific _popen and _pclose functions
    std::unique_ptr<FILE, decltype(&_pclose)> pipe(_popen(cmd, "r"), _pclose);
#else
    // Use the standard POSIX popen and pclose on other systems
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd, "r"), pclose);
#endif

    if (!pipe)
    {
        throw std::runtime_error("popen() failed!");
    }
    while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe.get()) != nullptr)
    {
        result += buffer.data();
    }
    return result;
}

// =============================================================================
// --- BASE FIXTURE FOR AUTOMATIC FILE CLEANUP ---
// =============================================================================
class FileCleanupTest : public ::testing::Test
{
protected:
    void SetUp() override
    {
        std::remove("test_output.csv");
        std::remove("recipe.json");
        std::remove("param_test.json");
        std::remove("sampler_test.json");
        std::remove("err.json");
    }

    void TearDown() override
    {
        std::remove("test_output.csv");
        std::remove("recipe.json");
        std::remove("param_test.json");
        std::remove("sampler_test.json");
        std::remove("err.json");
    }
};

// --- Parameterized Test Fixture now inherits from our cleanup fixture ---
using TestParam = std::tuple<std::string, TrialValue, bool>;

class DeterministicEngineTest : public FileCleanupTest,
                                public ::testing::WithParamInterface<TestParam>
{
};

// --- Sampler Test Fixture now inherits from our cleanup fixture ---
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

// --- Error Test Fixture now inherits from our cleanup fixture ---
class EngineErrorTests : public FileCleanupTest
{
};

// --- File Output Test Fixture now inherits from our cleanup fixture ---
class EngineFileOutputTest : public FileCleanupTest
{
};

// =============================================================================
// --- TEST CASES ---
// =============================================================================

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

// --- Basic Assignment Tests ---
INSTANTIATE_TEST_SUITE_P(
    AssignmentTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":123.45}]})", TrialValue(123.45), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]}]})", TrialValue(std::vector<double>{1.0, 2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":99.0},{"type":"execution_assignment","result_index":1,"function":"identity","args":[{"type":"variable_index","value":0}]}]})", TrialValue(99.0), false)));

// --- Binary and Unary Math Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    MathOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(30.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"subtract","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(-10.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"multiply","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(200.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":20},{"type":"literal_assignment","result_index":1,"value":10},{"type":"execution_assignment","result_index":2,"function":"divide","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(2.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":2},{"type":"literal_assignment","result_index":1,"value":8},{"type":"execution_assignment","result_index":2,"function":"power","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(256.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"execution_assignment","result_index":1,"function":"log","args":[10.0]}]})", TrialValue(std::log(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"execution_assignment","result_index":1,"function":"log10","args":[10.0]}]})", TrialValue(std::log10(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":2},{"type":"execution_assignment","result_index":1,"function":"exp","args":[2.0]}]})", TrialValue(std::exp(2.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_index":1,"function":"sin","args":[0.0]}]})", TrialValue(std::sin(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_index":1,"function":"cos","args":[0.0]}]})", TrialValue(std::cos(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_index":1,"function":"tan","args":[0.0]}]})", TrialValue(std::tan(0.0)), false)));

// --- Vector and Time-Series Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    VectorOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2,3]},{"type":"literal_assignment","result_index":1,"value":[4,5,6]},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(std::vector<double>{5.0, 7.0, 9.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["C","base","rate"],"per_trial_steps":[{"type":"literal_assignment","result_index":1,"value":100},{"type":"literal_assignment","result_index":2,"value":0.1},{"type":"execution_assignment","result_index":0,"function":"grow_series","args":[{"type":"variable_index","value":1},{"type":"variable_index","value":2},3.0]}]})", TrialValue(std::vector<double>{110.0, 121.0, 133.1}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["base","rates","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100},{"type":"literal_assignment","result_index":1,"value":[0.1,0.2]},{"type":"execution_assignment","result_index":2,"function":"compound_series","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(std::vector<double>{110.0, 132.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["series","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[100,110,125]},{"type":"execution_assignment","result_index":1,"function":"series_delta","args":[{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["series","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,70]},{"type":"execution_assignment","result_index":1,"function":"sum_series","args":[{"type":"variable_index","value":0}]}]})", TrialValue(100.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["start","end","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":50},{"type":"execution_assignment","result_index":2,"function":"interpolate_series","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},5.0]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0, 40.0, 50.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["A","B","C_in","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"literal_assignment","result_index":2,"value":30},{"type":"execution_assignment","result_index":3,"function":"compose_vector","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["current_rd","past_rd","period","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100.0},{"type":"literal_assignment","result_index":1,"value":[90.0,80.0,70.0]},{"type":"literal_assignment","result_index":2,"value":3.0},{"type":"execution_assignment","result_index":3,"function":"capitalize_expense","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]})", TrialValue(std::vector<double>{186.66666666666666, 80.0}), true)));

TEST_F(EngineErrorTests, ThrowsOnDeleteElementIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable_index":1,
        "variable_registry": ["my_vec", "A"],
        "per_trial_steps": [
            {"type":"literal_assignment","result_index":0,"value":[10.0, 20.0, 30.0]},
            {"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index", "value":0}, 5.0]}
        ]
    })");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnDeleteElementEmptyVector)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable_index":1,
        "variable_registry": ["empty_vec", "A"],
        "per_trial_steps": [
            {"type":"literal_assignment","result_index":0,"value":[]},
            {"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index", "value":0}, 0.0]}
        ]
    })");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

INSTANTIATE_TEST_SUITE_P(
    DeleteElementOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec","A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0},1.0]}]})", TrialValue(std::vector<double>{1.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec","A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0},0.0]}]})", TrialValue(std::vector<double>{2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec","A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0},2.0]}]})", TrialValue(std::vector<double>{1.0, 2.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec","A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0},-1.0]}]})", TrialValue(std::vector<double>{1.0, 2.0}), true) // Test negative index
        ));

// --- Nested Expression Test ---
INSTANTIATE_TEST_SUITE_P(
    NestedExpressionTest,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["A","B","C","D"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"literal_assignment","result_index":2,"value":5},{"type":"execution_assignment","result_index":3,"function":"multiply","args":[{"type":"variable_index","value":0},{"type":"execution_assignment","function":"subtract","args":[{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]}]})", TrialValue(150.0), false)));

// --- Mixed-Type Vector Math Tests ---
INSTANTIATE_TEST_SUITE_P(
    MixedTypeVectorMathTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"add","args":[{"type":"variable_index","value":0},5.0]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"add","args":[5.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"subtract","args":[{"type":"variable_index","value":0},3.0]}]})", TrialValue(std::vector<double>{7.0, 17.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"subtract","args":[100.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{90.0, 80.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,4,6]},{"type":"execution_assignment","result_index":1,"function":"multiply","args":[{"type":"variable_index","value":0},10.0]}]})", TrialValue(std::vector<double>{20.0, 40.0, 60.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"multiply","args":[0.5,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{5.0, 10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[100,200]},{"type":"execution_assignment","result_index":1,"function":"divide","args":[{"type":"variable_index","value":0},10.0]}]})", TrialValue(std::vector<double>{10.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,4,5]},{"type":"execution_assignment","result_index":1,"function":"divide","args":[100.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{50.0, 25.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,3,4]},{"type":"execution_assignment","result_index":1,"function":"power","args":[{"type":"variable_index","value":0},2.0]}]})", TrialValue(std::vector<double>{4.0, 9.0, 16.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2,3]},{"type":"execution_assignment","result_index":1,"function":"power","args":[2.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{2.0, 4.0, 8.0}), true)));

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

TEST_F(EngineErrorTests, ThrowsOnDivisionByZero)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100},{"type":"literal_assignment","result_index":1,"value":0},{"type":"execution_assignment","result_index":2,"function":"divide","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnVectorSizeMismatch)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2]},{"type":"literal_assignment","result_index":1,"value":[1,2,3]},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})");
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected std::runtime_error for vector size mismatch, but no exception was thrown.";
    }
    catch (const std::runtime_error &e)
    {
        EXPECT_THAT(e.what(), ::testing::HasSubstr("Vector size mismatch"));
    }
    catch (...)
    {
        FAIL() << "Expected std::runtime_error for vector size mismatch, but a different exception was thrown.";
    }
}

TEST_F(EngineErrorTests, ThrowsOnIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"get_element","args":[{"type":"variable_index","value":0},5.0]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnInvalidPertParams)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Pert","args":[100,50,200]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineFileOutputTest, WritesScalarOutputCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {
            "num_trials": 1,
            "output_file": "test_output.csv"
        },
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [
            {"type": "literal_assignment", "result_index": 0, "value": 123.45}
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    std::string output_path = engine.get_output_file_path();
    ASSERT_EQ(output_path, "test_output.csv");
    write_results_to_csv(output_path, results);

    std::string file_content = read_file_content("test_output.csv");
    std::string expected_content = "Result\n123.45\n";
    EXPECT_EQ(file_content, expected_content);
}

TEST_F(EngineFileOutputTest, WritesVectorOutputCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {
            "num_trials": 1,
            "output_file": "test_output.csv"
        },
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [
            {"type": "literal_assignment", "result_index": 0, "value": [10.1, 20.2, 30.3]}
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    std::string output_path = engine.get_output_file_path();
    ASSERT_EQ(output_path, "test_output.csv");
    write_results_to_csv(output_path, results);

    std::string file_content = read_file_content("test_output.csv");
    std::string expected_content = "Period_1,Period_2,Period_3\n10.1,20.2,30.3\n";
    EXPECT_EQ(file_content, expected_content);
}

TEST_F(EngineFileOutputTest, DoesNotWriteFileWhenNotSpecified)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [{"type": "literal_assignment", "result_index": 0, "value": 10}]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    engine.run();

    std::string output_path = engine.get_output_file_path();
    ASSERT_TRUE(output_path.empty());

    std::ifstream file("test_output.csv");
    EXPECT_FALSE(file.good());
}

// =============================================================================
// --- CSV-RELATED TESTS (RESTORED) ---
// =============================================================================
class CsvEngineTest : public FileCleanupTest
{
protected:
    void SetUp() override
    {
        FileCleanupTest::SetUp();
        std::ofstream csv_file("test_data.csv");
        csv_file << "ID,Value,Rate\n";
        csv_file << "1,100.5,0.05\n";
        csv_file << "2,200.0,0.06\n";
        csv_file << "3,-50.25,0.07\n";
        csv_file.close();

        std::ofstream bad_csv_file("bad_data.csv");
        bad_csv_file << "Header\n";
        bad_csv_file << "NotANumber\n";
        bad_csv_file.close();
    }

    void TearDown() override
    {
        std::remove("test_data.csv");
        std::remove("bad_data.csv");
        FileCleanupTest::TearDown();
    }
};

TEST_F(CsvEngineTest, ReadsVectorCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"} ]
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<std::vector<double>>(results[0]));
    const auto &result_vec = std::get<std::vector<double>>(results[0]);
    const std::vector<double> expected_vec = {100.5, 200.0, -50.25};

    ASSERT_EQ(result_vec.size(), expected_vec.size());
    for (size_t i = 0; i < result_vec.size(); ++i)
    {
        EXPECT_NEAR(result_vec[i], expected_vec[i], 1e-6);
    }
}

TEST_F(CsvEngineTest, ReadsScalarCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result_index": 0, "function": "read_csv_scalar",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Rate"}, 2.0 ]
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<double>(results[0]));
    double result_scalar = std::get<double>(results[0]);
    EXPECT_NEAR(result_scalar, 0.07, 1e-6);
}

TEST_F(CsvEngineTest, UsesPreloadedDataInTrial)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 2,
        "variable_registry": ["A", "B", "C"],
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result_index": 0, "function": "read_csv_scalar",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"}, 0 ]
            }
        ],
        "per_trial_steps": [
            {"type": "literal_assignment", "result_index": 1, "value": 10.0},
            {"type": "execution_assignment", "result_index": 2, "function": "add", "args": [{"type":"variable_index", "value":0}, {"type":"variable_index", "value":1}]}
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();
    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<double>(results[0]));
    double result_scalar = std::get<double>(results[0]);
    EXPECT_NEAR(result_scalar, 110.5, 1e-6);
}

TEST_F(CsvEngineTest, ThrowsOnFileNotFound)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "non_existent_file.csv"}, {"type": "string_literal", "value": "Value"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

TEST_F(CsvEngineTest, ThrowsOnColumnNotFound)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "NonExistentColumn"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

TEST_F(CsvEngineTest, ThrowsOnRowIndexOutOfBounds)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_scalar",
            "args": [{"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"}, 99.0]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

TEST_F(CsvEngineTest, ThrowsOnNonNumericData)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "bad_data.csv"}, {"type": "string_literal", "value": "Header"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}