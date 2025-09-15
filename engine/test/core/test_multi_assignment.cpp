#include "test/test_helpers.h"

class MultiAssignmentTest : public FileCleanupTest
{
};

TEST_F(MultiAssignmentTest, CorrectlyUnpacksVectorResult)
{
    // This recipe simulates:
    // let a, b = capitalize_expense(1, [1,1], 2)
    // The expected result for capitalize_expense is the vector [100.5, 1.0]
    // So, 'a' should be 100.5 and 'b' should be 1.0
    // We will set 'b' as the output variable to check the second value.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 1,
        "variable_registry": ["a", "b"],
        "per_trial_steps": [
            {
                "type": "multi_execution_assignment",
                "result_indices": [0, 1],
                "function": "capitalize_expense",
                "args": [
                    {"type": "scalar_literal", "value": 100.0},
                    {"type": "vector_literal", "value": [90.0, 80.0]},
                    {"type": "scalar_literal", "value": 2.0}
                ]
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe);

    // Test that the second variable ('b') gets the correct value
    SimulationEngine engine_b("recipe.json");
    auto results_b = engine_b.run();
    ASSERT_EQ(results_b.size(), 1);
    EXPECT_NEAR(std::get<double>(results_b[0]), 85.0, 1e-6); // Amortization = 90/2 + 80/2

    // Now, change the output index to test the first variable ('a')
    const std::string recipe_a = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["a", "b"],
        "per_trial_steps": [
            {
                "type": "multi_execution_assignment",
                "result_indices": [0, 1],
                "function": "capitalize_expense",
                "args": [
                    {"type": "scalar_literal", "value": 100.0},
                    {"type": "vector_literal", "value": [90.0, 80.0]},
                    {"type": "scalar_literal", "value": 2.0}
                ]
            }
        ]
    })";
    create_test_recipe("recipe_a.json", recipe_a);
    SimulationEngine engine_a("recipe_a.json");
    auto results_a = engine_a.run();
    ASSERT_EQ(results_a.size(), 1);
    EXPECT_NEAR(std::get<double>(results_a[0]), 145.0, 1e-6); // Asset = 100 + 90*(1/2)
}

TEST_F(MultiAssignmentTest, ThrowsOnResultCountMismatch)
{
    // Here, we expect 3 variables but capitalize_expense only returns 2.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a", "b", "c"],
        "per_trial_steps": [{
            "type": "multi_execution_assignment", "result_indices": [0, 1, 2], "function": "capitalize_expense",
            "args": [
                {"type": "scalar_literal", "value": 100},
                {"type": "vector_literal", "value": [90]},
                {"type": "scalar_literal", "value": 2}
            ]
        }]
    })";
    create_test_recipe("err.json", recipe);

    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception for result count mismatch.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::IncorrectArgumentCount);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("returned 2 values, but 3 were expected"));
    }
}

TEST_F(MultiAssignmentTest, ThrowsIfFunctionDoesNotReturnVector)
{
    // We try to multi-assign from 'log', which returns a scalar.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a", "b"],
        "per_trial_steps": [{
            "type": "multi_execution_assignment", "result_indices": [0, 1], "function": "log",
            "args": [{"type": "scalar_literal", "value": 10}]
        }]
    })";
    create_test_recipe("err.json", recipe);

    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception for non-vector multi-assignment.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::MismatchedArgumentType);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("did not return a vector for multi-assignment"));
    }
}