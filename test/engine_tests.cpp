#include <gtest/gtest.h>
#include <fstream>
#include <string>
#include <vector>
#include <tuple>
#include "engine/SimulationEngine.h"

// Helper function to create a test recipe file.
void create_test_recipe(const std::string &filename, const std::string &content)
{
    std::ofstream test_file(filename);
    test_file << content;
    test_file.close();
}

// --- Parameterized Test Fixture for Operations ---
using TestParam = std::tuple<std::string, TrialValue, bool>;

class EngineOperationTest : public ::testing::TestWithParam<TestParam>
{
};

// The single test block for all parameterized tests.
TEST_P(EngineOperationTest, ExecutesCorrectly)
{
    // 1. Arrange
    const auto &params = GetParam();
    const std::string &recipe_content = std::get<0>(params);
    const TrialValue &expected_result = std::get<1>(params);
    const bool is_vector_output = std::get<2>(params);

    const std::string filename = "param_test.json";
    create_test_recipe(filename, recipe_content);

    // 2. Act
    SimulationEngine engine(filename);
    std::vector<TrialValue> results = engine.run();

    // 3. Assert
    ASSERT_EQ(results.size(), 1);

    if (is_vector_output)
    {
        ASSERT_TRUE(std::holds_alternative<std::vector<double>>(results[0]));
        const auto &result_vec = std::get<std::vector<double>>(results[0]);
        const auto &expected_vec = std::get<std::vector<double>>(expected_result);
        ASSERT_EQ(result_vec.size(), expected_vec.size());
        for (size_t i = 0; i < result_vec.size(); ++i)
        {
            EXPECT_DOUBLE_EQ(result_vec[i], expected_vec[i]);
        }
    }
    else
    {
        ASSERT_TRUE(std::holds_alternative<double>(results[0]));
        double final_value = std::get<double>(results[0]);
        double expected_value = std::get<double>(expected_result);
        EXPECT_DOUBLE_EQ(final_value, expected_value);
    }
}

// --- Data for the Parameterized Tests ---

// Test suite for all binary operations
INSTANTIATE_TEST_SUITE_P(
    BinaryOps,
    EngineOperationTest,
    ::testing::Values(
        // Add
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":10},"B":{"type":"fixed","value":20}},"operations":[{"op_code":"add","args":["A","B"],"result":"C"}],"output_variable":"C"})", TrialValue(30.0), false),
        // Subtract
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":10},"B":{"type":"fixed","value":20}},"operations":[{"op_code":"subtract","args":["A","B"],"result":"C"}],"output_variable":"C"})", TrialValue(-10.0), false),
        // Multiply
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":10},"B":{"type":"fixed","value":20}},"operations":[{"op_code":"multiply","args":["A","B"],"result":"C"}],"output_variable":"C"})", TrialValue(200.0), false),
        // Divide
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":20},"B":{"type":"fixed","value":10}},"operations":[{"op_code":"divide","args":["A","B"],"result":"C"}],"output_variable":"C"})", TrialValue(2.0), false),
        // Power
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":2},"B":{"type":"fixed","value":8}},"operations":[{"op_code":"power","args":["A","B"],"result":"C"}],"output_variable":"C"})", TrialValue(256.0), false)));

// Test suite for time-series operations
INSTANTIATE_TEST_SUITE_P(
    TimeSeriesOps,
    EngineOperationTest,
    ::testing::Values(
        // grow_series
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"base":{"type":"fixed","value":100},"rate":{"type":"fixed","value":0.1},"years":{"type":"fixed","value":3}},"operations":[{"op_code":"grow_series","args":["base","rate","years"],"result":"C"}],"output_variable":"C"})", TrialValue(std::vector<double>{110.0, 121.0, 133.1}), true),
        // get_element (last)
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"series":{"type":"fixed","value":[10,20,30]}},"operations":[{"op_code":"get_element","args":["series",-1],"result":"C"}],"output_variable":"C"})", TrialValue(30.0), false),
        // series_delta
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"series":{"type":"fixed","value":[100,110,125]}},"operations":[{"op_code":"series_delta","args":["series"],"result":"C"}],"output_variable":"C"})", TrialValue(std::vector<double>{0.0, 10.0, 15.0}), true)));

INSTANTIATE_TEST_SUITE_P(
    UnaryAndSpecialOps,
    EngineOperationTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":10}},"operations":[{"op_code":"log","args":["A"],"result":"C"}],"output_variable":"C"})", TrialValue(std::log(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":10}},"operations":[{"op_code":"log10","args":["A"],"result":"C"}],"output_variable":"C"})", TrialValue(std::log10(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":2}},"operations":[{"op_code":"exp","args":["A"],"result":"C"}],"output_variable":"C"})", TrialValue(std::exp(2.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":0}},"operations":[{"op_code":"sin","args":["A"],"result":"C"}],"output_variable":"C"})", TrialValue(std::sin(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":0}},"operations":[{"op_code":"cos","args":["A"],"result":"C"}],"output_variable":"C"})", TrialValue(std::cos(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"A":{"type":"fixed","value":0}},"operations":[{"op_code":"tan","args":["A"],"result":"C"}],"output_variable":"C"})", TrialValue(std::tan(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"base":{"type":"fixed","value":100},"rates":{"type":"fixed","value":[0.1,0.2]}},"operations":[{"op_code":"compound_series","args":["base","rates"],"result":"C"}],"output_variable":"C"})", TrialValue(std::vector<double>{110.0, 132.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"series":{"type":"fixed","value":[10,20,70]}},"operations":[{"op_code":"sum_series","args":["series"],"result":"C"}],"output_variable":"C"})", TrialValue(100.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"rate":{"type":"fixed","value":0.1},"cfs":{"type":"fixed","value":[100,110]}},"operations":[{"op_code":"npv","args":["rate","cfs"],"result":"C"}],"output_variable":"C"})", TrialValue(100.0 / 1.1 + 110.0 / (1.1 * 1.1)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"r1":{"type":"fixed","value":10},"r2":{"type":"fixed","value":20},"r3":{"type":"fixed","value":30}},"operations":[{"op_code":"compose_vector","args":["r1","r2","r3"],"result":"C"}],"output_variable":"C"})", TrialValue(std::vector<double>{10.0, 20.0, 30.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"inputs":{"start":{"type":"fixed","value":10},"end":{"type":"fixed","value":50},"years":{"type":"fixed","value":5}},"operations":[{"op_code":"interpolate_series","args":["start","end","years"],"result":"C"}],"output_variable":"C"})", TrialValue(std::vector<double>{10.0, 20.0, 30.0, 40.0, 50.0}), true)));

TEST(EngineErrorTests, ThrowsOnInvalidFilePath)
{
    ASSERT_THROW(SimulationEngine engine("non_existent_file.json"), std::runtime_error);
}

TEST(EngineErrorTests, ThrowsOnMalformedJson)
{
    create_test_recipe("malformed.json", R"({ "key": "value" )");
    ASSERT_THROW(SimulationEngine engine("malformed.json"), nlohmann::json::parse_error);
}

TEST(EngineErrorTests, ThrowsOnUndefinedVariable)
{
    create_test_recipe("undefined_var.json", R"({
        "simulation_config": { "num_trials": 1 }, "inputs": {},
        "operations": [{ "op_code": "add", "args": ["A", "B"], "result": "C" }],
        "output_variable": "C"
    })");
    SimulationEngine engine("undefined_var.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST(EngineErrorTests, ThrowsOnDivisionByZero)
{
    create_test_recipe("div_zero.json", R"({
        "simulation_config": { "num_trials": 1 }, "inputs": {
            "A": { "type": "fixed", "value": 100.0 }, "B": { "type": "fixed", "value": 0.0 }
        }, "operations": [{ "op_code": "divide", "args": ["A", "B"], "result": "C" }],
        "output_variable": "C"
    })");
    SimulationEngine engine("div_zero.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST(EngineErrorTests, ThrowsOnVectorSizeMismatch)
{
    create_test_recipe("vec_mismatch.json", R"({
        "simulation_config": { "num_trials": 1 }, "inputs": {
            "vec1": { "type": "fixed", "value": [1, 2, 3] },
            "vec2": { "type": "fixed", "value": [4, 5] }
        }, "operations": [{ "op_code": "add", "args": ["vec1", "vec2"], "result": "C" }],
        "output_variable": "C"
    })");
    SimulationEngine engine("vec_mismatch.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

// Test case for a deeply nested, multi-level recursive expression.
TEST(EngineLogicTests, MultiLevelRecursiveExpression)
{
    create_test_recipe("multilevel_expression.json", R"({
        "simulation_config": { "num_trials": 1 },
        "inputs": {
            "A": { "type": "fixed", "value": 10.0 },
            "B": { "type": "fixed", "value": 5.0 },
            "C": { "type": "fixed", "value": 20.0 },
            "D": { "type": "fixed", "value": 8.0 }
        },
        "operations": [{
            "op_code": "add",
            "args": [
                "A",
                {
                    "op_code": "multiply",
                    "args": [
                        "B",
                        {
                            "op_code": "subtract",
                            "args": ["C", "D"]
                        }
                    ]
                }
            ],
            "result": "FinalValue"
        }],
        "output_variable": "FinalValue"
    })");

    SimulationEngine engine("multilevel_expression.json");
    std::vector<TrialValue> results = engine.run();
    ASSERT_EQ(results.size(), 1);
    double final_value = std::get<double>(results[0]);
    EXPECT_DOUBLE_EQ(final_value, 70.0);
}