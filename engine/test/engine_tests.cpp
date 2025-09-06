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
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","per_trial_steps":[{"type":"literal_assignment","result":"A","value":123.45}]})", TrialValue(123.45), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[1.0,2.0,3.0]}]})", TrialValue(std::vector<double>{1.0, 2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","per_trial_steps":[{"type":"literal_assignment","result":"A","value":99.0},{"type":"execution_assignment","result":"B","function":"identity","args":["A"]}]})", TrialValue(99.0), false)));

// --- Binary and Unary Math Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    MathOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})", TrialValue(30.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"execution_assignment","result":"C","function":"subtract","args":["A","B"]}]})", TrialValue(-10.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"execution_assignment","result":"C","function":"multiply","args":["A","B"]}]})", TrialValue(200.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":20},{"type":"literal_assignment","result":"B","value":10},{"type":"execution_assignment","result":"C","function":"divide","args":["A","B"]}]})", TrialValue(2.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":2},{"type":"literal_assignment","result":"B","value":8},{"type":"execution_assignment","result":"C","function":"power","args":["A","B"]}]})", TrialValue(256.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","per_trial_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"execution_assignment","result":"B","function":"log","args":["A"]}]})", TrialValue(std::log(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","per_trial_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"execution_assignment","result":"B","function":"log10","args":["A"]}]})", TrialValue(std::log10(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","per_trial_steps":[{"type":"literal_assignment","result":"A","value":2},{"type":"execution_assignment","result":"B","function":"exp","args":["A"]}]})", TrialValue(std::exp(2.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","per_trial_steps":[{"type":"literal_assignment","result":"A","value":0},{"type":"execution_assignment","result":"B","function":"sin","args":["A"]}]})", TrialValue(std::sin(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","per_trial_steps":[{"type":"literal_assignment","result":"A","value":0},{"type":"execution_assignment","result":"B","function":"cos","args":["A"]}]})", TrialValue(std::cos(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"B","per_trial_steps":[{"type":"literal_assignment","result":"A","value":0},{"type":"execution_assignment","result":"B","function":"tan","args":["A"]}]})", TrialValue(std::tan(0.0)), false)));

// --- Vector and Time-Series Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    VectorOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[1,2,3]},{"type":"literal_assignment","result":"B","value":[4,5,6]},{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})", TrialValue(std::vector<double>{5.0, 7.0, 9.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"base","value":100},{"type":"literal_assignment","result":"rate","value":0.1},{"type":"execution_assignment","result":"C","function":"grow_series","args":["base","rate",3]}]})", TrialValue(std::vector<double>{110.0, 121.0, 133.1}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"base","value":100},{"type":"literal_assignment","result":"rates","value":[0.1,0.2]},{"type":"execution_assignment","result":"C","function":"compound_series","args":["base","rates"]}]})", TrialValue(std::vector<double>{110.0, 132.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"series","value":[100,110,125]},{"type":"execution_assignment","result":"C","function":"series_delta","args":["series"]}]})", TrialValue(std::vector<double>{10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"series","value":[10,20,70]},{"type":"execution_assignment","result":"C","function":"sum_series","args":["series"]}]})", TrialValue(100.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"start","value":10},{"type":"literal_assignment","result":"end","value":50},{"type":"execution_assignment","result":"C","function":"interpolate_series","args":["start","end",5]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0, 40.0, 50.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"literal_assignment","result":"C_in","value":30},{"type":"execution_assignment","result":"C","function":"compose_vector","args":["A","B","C_in"]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"current_rd","value":100.0},{"type":"literal_assignment","result":"past_rd","value":[90.0,80.0,70.0]},{"type":"literal_assignment","result":"period","value":3.0},{"type":"execution_assignment","result":"C","function":"capitalize_expense","args":["current_rd","past_rd","period"]}]})", TrialValue(std::vector<double>{186.66666666666666, 80.0}), true)));

TEST_F(EngineErrorTests, ThrowsOnDeleteElementIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable":"A",
        "per_trial_steps": [
            {"type":"literal_assignment","result":"my_vec","value":[10.0, 20.0, 30.0]},
            {"type":"execution_assignment","result":"A","function":"delete_element","args":["my_vec", 5.0]}
        ]
    })");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnDeleteElementEmptyVector)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable":"A",
        "per_trial_steps": [
            {"type":"literal_assignment","result":"empty_vec","value":[]},
            {"type":"execution_assignment","result":"A","function":"delete_element","args":["empty_vec", 0.0]}
        ]
    })");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

INSTANTIATE_TEST_SUITE_P(
    DeleteElementOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","per_trial_steps":[{"type":"literal_assignment","result":"my_vec","value":[1.0,2.0,3.0]},{"type":"execution_assignment","result":"A","function":"delete_element","args":["my_vec",1]}]})", TrialValue(std::vector<double>{1.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","per_trial_steps":[{"type":"literal_assignment","result":"my_vec","value":[1.0,2.0,3.0]},{"type":"execution_assignment","result":"A","function":"delete_element","args":["my_vec",0]}]})", TrialValue(std::vector<double>{2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","per_trial_steps":[{"type":"literal_assignment","result":"my_vec","value":[1.0,2.0,3.0]},{"type":"execution_assignment","result":"A","function":"delete_element","args":["my_vec",2]}]})", TrialValue(std::vector<double>{1.0, 2.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"A","per_trial_steps":[{"type":"literal_assignment","result":"my_vec","value":[1.0,2.0,3.0]},{"type":"execution_assignment","result":"A","function":"delete_element","args":["my_vec",-1]}]})", TrialValue(std::vector<double>{1.0, 2.0}), true) // Test negative index
        ));

// --- Nested Expression Test ---
INSTANTIATE_TEST_SUITE_P(
    NestedExpressionTest,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"D","per_trial_steps":[{"type":"literal_assignment","result":"A","value":10},{"type":"literal_assignment","result":"B","value":20},{"type":"literal_assignment","result":"C","value":5},{"type":"execution_assignment","result":"D","function":"multiply","args":["A",{"function":"subtract","args":["B","C"]}]}]})", TrialValue(150.0), false)));

// --- Mixed-Type Vector Math Tests ---
INSTANTIATE_TEST_SUITE_P(
    MixedTypeVectorMathTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[10,20,30]},{"type":"execution_assignment","result":"C","function":"add","args":["A",5.0]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[10,20,30]},{"type":"execution_assignment","result":"C","function":"add","args":[5.0,"A"]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[10,20]},{"type":"execution_assignment","result":"C","function":"subtract","args":["A",3.0]}]})", TrialValue(std::vector<double>{7.0, 17.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[10,20]},{"type":"execution_assignment","result":"C","function":"subtract","args":[100.0,"A"]}]})", TrialValue(std::vector<double>{90.0, 80.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[2,4,6]},{"type":"execution_assignment","result":"C","function":"multiply","args":["A",10.0]}]})", TrialValue(std::vector<double>{20.0, 40.0, 60.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[10,20,30]},{"type":"execution_assignment","result":"C","function":"multiply","args":[0.5,"A"]}]})", TrialValue(std::vector<double>{5.0, 10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[100,200]},{"type":"execution_assignment","result":"C","function":"divide","args":["A",10.0]}]})", TrialValue(std::vector<double>{10.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[2,4,5]},{"type":"execution_assignment","result":"C","function":"divide","args":[100.0,"A"]}]})", TrialValue(std::vector<double>{50.0, 25.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[2,3,4]},{"type":"execution_assignment","result":"C","function":"power","args":["A",2.0]}]})", TrialValue(std::vector<double>{4.0, 9.0, 16.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[1,2,3]},{"type":"execution_assignment","result":"C","function":"power","args":[2.0,"A"]}]})", TrialValue(std::vector<double>{2.0, 4.0, 8.0}), true)));

TEST_F(EngineSamplerTest, Normal)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Normal","args":[100.0,15.0]}]})", 20000, 100.0, 0.5);
}

TEST_F(EngineSamplerTest, Pert)
{
    double expected_mean = (50.0 + 4.0 * 100.0 + 200.0) / 6.0; // ~125
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Pert","args":[50,100,200]}]})", 20000, expected_mean, 2.0, true, 50.0, 200.0);
}

TEST_F(EngineSamplerTest, Uniform)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Uniform","args":[-10,10]}]})", 20000, 0.0, 0.5, true, -10.0, 10.0);
}

TEST_F(EngineSamplerTest, Triangular)
{
    double expected_mean = (10.0 + 20.0 + 60.0) / 3.0; // ~30.0
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Triangular","args":[10,20,60]}]})", 20000, expected_mean, 1.0, true, 10.0, 60.0);
}

TEST_F(EngineSamplerTest, Bernoulli)
{
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Bernoulli","args":[0.75]}]})", 20000, 0.75, 0.01, true, 0.0, 1.0);
}

TEST_F(EngineSamplerTest, Beta)
{
    double expected_mean = 2.0 / (2.0 + 5.0); // ~0.2857
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Beta","args":[2.0, 5.0]}]})", 20000, expected_mean, 0.01, true, 0.0, 1.0);
}

TEST_F(EngineSamplerTest, Lognormal)
{
    double log_mean = 2.0, log_stddev = 0.5;
    double expected_mean = std::exp(log_mean + (log_stddev * log_stddev) / 2.0); // ~8.37
    RunAndAnalyze(R"({"simulation_config":{"num_trials":20000},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Lognormal","args":[2.0,0.5]}]})", 20000, expected_mean, 0.5, true, 0.0, 1e9);
}

TEST_F(EngineErrorTests, ThrowsOnUndefinedVariable)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})");
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected std::runtime_error for undefined function in recipe";
    }
    catch (const std::runtime_error &e)
    {
        EXPECT_STREQ(e.what(), "Argument 'A' is not a known variable.");
    }
    catch (...)
    {
        FAIL() << "Expected std::runtime_error for undefined function in recipe";
    }
}

TEST_F(EngineErrorTests, ThrowsOnDivisionByZero)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":100},{"type":"literal_assignment","result":"B","value":0},{"type":"execution_assignment","result":"C","function":"divide","args":["A","B"]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnVectorSizeMismatch)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[1,2]},{"type":"literal_assignment","result":"B","value":[1,2,3]},{"type":"execution_assignment","result":"C","function":"add","args":["A","B"]}]})");
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected std::runtime_error for vector size mismatch, but no exception was thrown.";
    }
    catch (const std::runtime_error &e)
    {
        EXPECT_STREQ(e.what(), "L-1: In function 'add': Vector size mismatch: element-wise operation requires vectors of the same length, but got sizes 2 and 3.");
    }
    catch (...)
    {
        FAIL() << "Expected std::runtime_error for vector size mismatch, but a different exception was thrown.";
    }
}

TEST_F(EngineErrorTests, ThrowsOnIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"C","per_trial_steps":[{"type":"literal_assignment","result":"A","value":[10,20]},{"type":"execution_assignment","result":"C","function":"get_element","args":["A",5]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnInvalidPertParams)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"X","per_trial_steps":[{"type":"execution_assignment","result":"X","function":"Pert","args":[100,50,200]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

// --- Tests for Argument Count Checks ---
// Helper macro to reduce boilerplate in arity tests

#define TEST_ARITY(function_name, json_args, expected_error_msg)                                                                                                                                                                                                                       \
    {                                                                                                                                                                                                                                                                                  \
        SCOPED_TRACE("Testing arity for function: " + std::string(function_name));                                                                                                                                                                                                     \
        create_test_recipe("err.json", "{\"simulation_config\":{\"num_trials\":1},\"output_variable\":\"X\",\"per_trial_steps\":[{\"type\":\"execution_assignment\",\"result\":\"X\",\"function\":\"" + std::string(function_name) + "\",\"args\":" + std::string(json_args) + "}]}"); \
        try                                                                                                                                                                                                                                                                            \
        {                                                                                                                                                                                                                                                                              \
            SimulationEngine engine("err.json");                                                                                                                                                                                                                                       \
            engine.run();                                                                                                                                                                                                                                                              \
            FAIL() << "Expected std::runtime_error for function '" << function_name << "', but no exception was thrown.";                                                                                                                                                              \
        }                                                                                                                                                                                                                                                                              \
        catch (const std::runtime_error &e)                                                                                                                                                                                                                                            \
        {                                                                                                                                                                                                                                                                              \
            EXPECT_STREQ(e.what(), expected_error_msg);                                                                                                                                                                                                                                \
        }                                                                                                                                                                                                                                                                              \
        catch (...)                                                                                                                                                                                                                                                                    \
        {                                                                                                                                                                                                                                                                              \
            FAIL() << "Expected std::runtime_error for function '" << function_name << "', but a different exception was thrown.";                                                                                                                                                     \
        }                                                                                                                                                                                                                                                                              \
    }

TEST_F(EngineErrorTests, AllSamplersThrowOnIncorrectArgCount)
{
    TEST_ARITY("Normal", "[1.0]", "L-1: In function 'Normal': Function 'Normal' requires 2 arguments: mean, stddev.");
    TEST_ARITY("Uniform", "[1.0, 2.0, 3.0]", "L-1: In function 'Uniform': Function 'Uniform' requires 2 arguments: min, max.");
    TEST_ARITY("Bernoulli", "[]", "L-1: In function 'Bernoulli': Function 'Bernoulli' requires 1 argument: p.");
    TEST_ARITY("Lognormal", "[1.0]", "L-1: In function 'Lognormal': Function 'Lognormal' requires 2 arguments: log_mean, log_stddev.");
    TEST_ARITY("Beta", "[1.0]", "L-1: In function 'Beta': Function 'Beta' requires 2 arguments: alpha, beta.");
    TEST_ARITY("Pert", "[1.0, 2.0]", "L-1: In function 'Pert': Function 'Pert' requires 3 arguments: min, mostLikely, max.");
    TEST_ARITY("Triangular", "[1.0, 2.0, 3.0, 4.0]", "L-1: In function 'Triangular': Function 'Triangular' requires 3 arguments: min, mostLikely, max.");
}

TEST_F(EngineErrorTests, AllOperationsThrowOnIncorrectArgCount)
{
    // 1-argument functions
    TEST_ARITY("log", "[]", "L-1: In function 'log': Function 'log' requires 1 argument.");
    TEST_ARITY("log10", "[1.0, 2.0]", "L-1: In function 'log10': Function 'log10' requires 1 argument.");
    TEST_ARITY("exp", "[]", "L-1: In function 'exp': Function 'exp' requires 1 argument.");
    TEST_ARITY("sin", "[1.0, 2.0]", "L-1: In function 'sin': Function 'sin' requires 1 argument.");
    TEST_ARITY("cos", "[]", "L-1: In function 'cos': Function 'cos' requires 1 argument.");
    TEST_ARITY("tan", "[1.0, 2.0]", "L-1: In function 'tan': Function 'tan' requires 1 argument.");
    TEST_ARITY("identity", "[]", "L-1: In function 'identity': Function 'identity' requires exactly 1 argument.");
    TEST_ARITY("sum_series", "[[1,2], [3,4]]", "L-1: In function 'sum_series': Function 'sum_series' requires 1 argument.");
    TEST_ARITY("series_delta", "[]", "L-1: In function 'series_delta': Function 'series_delta' requires 1 argument.");

    // 2-argument functions
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable":"X","per_trial_steps":[{"type":"literal_assignment","result":"v","value":[1,2]},{"type":"execution_assignment","result":"X","function":"compound_series","args":["v"]}]})");
    SimulationEngine engine_cs("err.json");
    ASSERT_THROW(engine_cs.run(), std::runtime_error);
    TEST_ARITY("npv", "[0.05, [1,2], 3.0]", "L-1: In function 'npv': Function 'npv' requires 2 arguments.");
    TEST_ARITY("get_element", "[1]", "L-1: In function 'get_element': Function 'get_element' requires 2 arguments.");
    TEST_ARITY("delete_element", "[[1,2]]", "L-1: In function 'delete_element': Function 'delete_element' requires 2 arguments.");
    TEST_ARITY("read_csv_vector", R"([{"type": "string_literal", "value": "f.csv"}])", "L-1: In function 'read_csv_vector': Function 'read_csv_vector' requires 2 arguments.");

    // 3-argument functions
    TEST_ARITY("grow_series", "[1, 0.1]", "L-1: In function 'grow_series': Function 'grow_series' requires 3 arguments.");
    TEST_ARITY("interpolate_series", "[1, 10, 5, 4]", "L-1: In function 'interpolate_series': Function 'interpolate_series' requires 3 arguments.");
    TEST_ARITY("capitalize_expense", "[1, [2,3]]", "L-1: In function 'capitalize_expense': Function 'capitalize_expense' requires 3 arguments.");
    TEST_ARITY("read_csv_scalar", R"([{"type": "string_literal", "value": "f.csv"}, {"type": "string_literal", "value": "c"}])", "L-1: In function 'read_csv_scalar': Function 'read_csv_scalar' requires 3 arguments.");
}

TEST_F(EngineFileOutputTest, WritesScalarOutputCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {
            "num_trials": 1,
            "output_file": "test_output.csv"
        },
        "output_variable": "A",
        "per_trial_steps": [
            {"type": "literal_assignment", "result": "A", "value": 123.45}
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
        "output_variable": "A",
        "per_trial_steps": [
            {"type": "literal_assignment", "result": "A", "value": [10.1, 20.2, 30.3]}
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
        "output_variable": "A",
        "per_trial_steps": [{"type": "literal_assignment", "result": "A", "value": 10}]
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
// --- FIXTURE FOR CSV-RELATED TESTS ---
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
        "output_variable": "A",
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result": "A", "function": "read_csv_vector",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"} ]
            }
        ],
        "per_trial_steps": [{"type": "execution_assignment", "result": "A", "function": "identity", "args": ["A"]}]
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
        "output_variable": "A",
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result": "A", "function": "read_csv_scalar",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Rate"}, 2.0 ]
            }
        ],
        "per_trial_steps": [{"type": "execution_assignment", "result": "A", "function": "identity", "args": ["A"]}]
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
        "output_variable": "C",
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result": "A", "function": "read_csv_scalar",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"}, 0 ]
            }
        ],
        "per_trial_steps": [
            {"type": "literal_assignment", "result": "B", "value": 10.0},
            {"type": "execution_assignment", "result": "C", "function": "add", "args": ["A", "B"]}
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
        "simulation_config": {"num_trials": 1}, "output_variable": "A",
        "pre_trial_steps": [{ "type": "execution_assignment", "result": "A", "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "non_existent_file.csv"}, {"type": "string_literal", "value": "Value"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

TEST_F(CsvEngineTest, ThrowsOnColumnNotFound)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable": "A",
        "pre_trial_steps": [{ "type": "execution_assignment", "result": "A", "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "NonExistentColumn"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

TEST_F(CsvEngineTest, ThrowsOnRowIndexOutOfBounds)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable": "A",
        "pre_trial_steps": [{ "type": "execution_assignment", "result": "A", "function": "read_csv_scalar",
            "args": [{"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"}, 99.0]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

TEST_F(CsvEngineTest, ThrowsOnNonNumericData)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable": "A",
        "pre_trial_steps": [{ "type": "execution_assignment", "result": "A", "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "bad_data.csv"}, {"type": "string_literal", "value": "Header"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

// =============================================================================
// --- TEST FIXTURE FOR PREVIEW MODE ---
// =============================================================================
class EnginePreviewModeTest : public FileCleanupTest
{
};

TEST_F(EnginePreviewModeTest, OutputsCorrectJsonForDeterministicScalar)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable": "a",
        "per_trial_steps": [{"type": "literal_assignment", "result": "a", "value": 123.45678}]
    })";
    create_test_recipe("preview_test.json", recipe);

#ifdef _WIN32
    std::string command = ".\\build\\bin\\Release\\vse.exe --preview preview_test.json";
#else
    std::string command = "./build/bin/vse --preview preview_test.json";
#endif

    std::string output = exec_command(command.c_str());

    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "success");
    EXPECT_EQ(json_out["type"], "scalar");
    EXPECT_NEAR(json_out["value"], 123.4568, 1e-5);
}

TEST_F(EnginePreviewModeTest, OutputsCorrectJsonForStochasticScalar)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 100}, "output_variable": "a",
        "per_trial_steps": [{"type": "execution_assignment", "result": "a", "function": "Normal", "args": [100, 0]}]
    })";
    create_test_recipe("preview_test.json", recipe);

#ifdef _WIN32
    std::string command = ".\\build\\bin\\Release\\vse.exe --preview preview_test.json";
#else
    std::string command = "./build/bin/vse --preview preview_test.json";
#endif

    std::string output = exec_command(command.c_str());

    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "success");
    EXPECT_EQ(json_out["type"], "scalar");
    EXPECT_NEAR(json_out["value"], 100.0, 1e-5);
}

TEST_F(EnginePreviewModeTest, OutputsCorrectJsonForVector)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable": "a",
        "per_trial_steps": [{"type": "literal_assignment", "result": "a", "value": [1.11111, 2.22222, 3.33333]}]
    })";
    create_test_recipe("preview_test.json", recipe);

#ifdef _WIN32
    std::string command = ".\\build\\bin\\Release\\vse.exe --preview preview_test.json";
#else
    std::string command = "./build/bin/vse --preview preview_test.json";
#endif

    std::string output = exec_command(command.c_str());

    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "success");
    EXPECT_EQ(json_out["type"], "vector");
    ASSERT_EQ(json_out["value"].size(), 3);
    EXPECT_NEAR(json_out["value"][0], 1.1111, 1e-5);
    EXPECT_NEAR(json_out["value"][1], 2.2222, 1e-5);
    EXPECT_NEAR(json_out["value"][2], 3.3333, 1e-5);
}

TEST_F(EnginePreviewModeTest, OutputsErrorJsonOnRuntimeError)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable": "a",
        "per_trial_steps": [{"type": "execution_assignment", "result": "a", "function": "divide", "args": [1, 0]}]
    })";
    create_test_recipe("preview_test.json", recipe);

// On Windows, popen captures stdout, but stderr from the child might go to the parent's stderr.
// On Unix, we can redirect stderr to stdout to capture it. This is the simplest cross-platform way for this test.
#ifdef _WIN32
    std::string command = ".\\build\\bin\\Release\\vse.exe --preview preview_test.json";
#else
    std::string command = "./build/bin/vse --preview preview_test.json 2>&1";
#endif

    std::string output = exec_command(command.c_str());

    // In case of a runtime error, the engine should still produce a valid JSON error message.
    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "error");
    ASSERT_TRUE(json_out.contains("message"));
    EXPECT_THAT(json_out["message"].get<std::string>(), ::testing::HasSubstr("Division by zero"));
}