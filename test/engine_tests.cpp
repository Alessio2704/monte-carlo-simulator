#include <gtest/gtest.h>
#include <fstream>
#include "engine/SimulationEngine.h"

// Helper function to create a test recipe file.
// This avoids duplicating the ofstream code in every test case.
void create_test_recipe(const std::string &filename, const std::string &content)
{
    std::ofstream test_file(filename);
    test_file << content;
    test_file.close();
}

// --- Test Suite for the SimulationEngine ---

// Test case for a basic valid operation.
TEST(EngineTests, BasicAddition)
{
    create_test_recipe("add.json", R"({
        "simulation_config": { "num_trials": 1 }, "inputs": {
            "A": { "type": "fixed", "value": 15.5 }, "B": { "type": "fixed", "value": 24.5 }
        }, "operations": [{ "op_code": "add", "args": ["A", "B"], "result": "C" }],
        "output_variable": "C"
    })");

    SimulationEngine engine("add.json");
    auto results = engine.run();
    ASSERT_EQ(results.size(), 1);
    EXPECT_DOUBLE_EQ(std::get<double>(results[0]), 40.0);
}

// Test case for a complex, nested expression.
TEST(EngineTests, RecursiveExpression)
{
    create_test_recipe("expression.json", R"({
        "simulation_config": { "num_trials": 1 }, "inputs": {
            "EBIT": { "type": "fixed", "value": 100.0 }, "tax_rate": { "type": "fixed", "value": 0.21 }
        }, "operations": [{
            "op_code": "multiply",
            "args": ["EBIT", { "op_code": "subtract", "args": [1.0, "tax_rate"] }], "result": "NOPAT"
        }], "output_variable": "NOPAT"
    })");

    SimulationEngine engine("expression.json");
    auto results = engine.run();
    ASSERT_EQ(results.size(), 1);
    EXPECT_DOUBLE_EQ(std::get<double>(results[0]), 79.0);
}

// --- EDGE CASE TESTS ---

// Test what happens with an invalid JSON file path.
TEST(EngineTests, ThrowsOnInvalidFilePath)
{
    // The ASSERT_THROW macro from GoogleTest checks if a piece of code
    // throws an exception of a specific type.
    ASSERT_THROW(SimulationEngine engine("non_existent_file.json"), std::runtime_error);
}

// Test what happens if the JSON is malformed.
TEST(EngineTests, ThrowsOnMalformedJson)
{
    create_test_recipe("malformed.json", R"({ "key": "value" )"); // Missing closing brace
    ASSERT_THROW(SimulationEngine engine("malformed.json"), nlohmann::json::parse_error);
}

// Test what happens if a variable is used but not defined.
TEST(EngineTests, ThrowsOnUndefinedVariable)
{
    create_test_recipe("undefined_var.json", R"({
        "simulation_config": { "num_trials": 1 }, "inputs": {},
        "operations": [{ "op_code": "add", "args": ["A", "B"], "result": "C" }],
        "output_variable": "C"
    })");

    SimulationEngine engine("undefined_var.json");
    // We expect the `run()` method to throw, as that's when variables are resolved.
    ASSERT_THROW(engine.run(), std::runtime_error);
}

// Test division by zero.
TEST(EngineTests, ThrowsOnDivisionByZero)
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

// Test vector size mismatch in an element-wise operation.
TEST(EngineTests, ThrowsOnVectorSizeMismatch)
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

TEST(EngineTests, MultiLevelRecursiveExpression)
{
    // 1. Arrange: Create a recipe to calculate (A + (B * (C - D)))
    // Expected result: (10 + (5 * (20 - 8))) = (10 + (5 * 12)) = (10 + 60) = 70
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

    // 2. Act
    SimulationEngine engine("multilevel_expression.json");
    std::vector<TrialValue> results = engine.run();

    // 3. Assert
    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<double>(results[0]));
    double final_value = std::get<double>(results[0]);
    EXPECT_DOUBLE_EQ(final_value, 70.0);
}