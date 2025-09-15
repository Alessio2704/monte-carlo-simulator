#include "test/test_helpers.h"

class MultiAssignmentTest : public FileCleanupTest
{
};

TEST_F(MultiAssignmentTest, CorrectlyUnpacksVectorResultInPerTrial)
{
    // Simulates: let assets, amortization = capitalize_expense(...)
    // capitalize_expense(100, [90, 80], 2) -> returns vector [145.0, 85.0]
    // We will test that both variables get the correct values assigned.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["assets", "amortization"],
        "per_trial_steps": [
            {
                "type": "multi_execution_assignment", "result_indices": [0, 1], "function": "capitalize_expense",
                "args": [
                    {"type": "scalar_literal", "value": 100.0},
                    {"type": "vector_literal", "value": [90.0, 80.0]},
                    {"type": "scalar_literal", "value": 2.0}
                ]
            }
        ]
    })";

    // Test 1: Check the first variable ('assets')
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine_assets("recipe.json");
    auto results_assets = engine_assets.run();
    ASSERT_EQ(std::get<double>(results_assets[0]), 145.0);

    // Test 2: Modify recipe to check the second variable ('amortization')
    const std::string recipe_amort = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 1, 
        "variable_registry": ["assets", "amortization"],
        "per_trial_steps": [
            {
                "type": "multi_execution_assignment", "result_indices": [0, 1], "function": "capitalize_expense",
                "args": [
                    {"type": "scalar_literal", "value": 100.0},
                    {"type": "vector_literal", "value": [90.0, 80.0]},
                    {"type": "scalar_literal", "value": 2.0}
                ]
            }
        ]
    })";
    create_test_recipe("recipe2.json", recipe_amort);
    SimulationEngine engine_amort("recipe2.json");
    auto results_amort = engine_amort.run();
    ASSERT_EQ(std::get<double>(results_amort[0]), 85.0);
}

TEST_F(MultiAssignmentTest, CorrectlyUnpacksInPreTrialAndIsUsedInPerTrial)
{
    // Simulates:
    // [Pre-Trial] let assets, amortization = capitalize_expense(...)
    // [Per-Trial] let final_val = assets + amortization
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 2, 
        "variable_registry": ["assets", "amortization", "final_val"],
        "pre_trial_steps": [
            {
                "type": "multi_execution_assignment", "result_indices": [0, 1], "function": "capitalize_expense",
                "args": [
                    {"type": "scalar_literal", "value": 100.0},
                    {"type": "vector_literal", "value": [90.0, 80.0]},
                    {"type": "scalar_literal", "value": 2.0}
                ]
            }
        ],
        "per_trial_steps": [
            {
                "type": "execution_assignment", "result_index": 2, "function": "add",
                "args": [
                    {"type": "variable_index", "value": 0},
                    {"type": "variable_index", "value": 1}
                ]
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 230.0); // 145.0 + 85.0
}

TEST_F(MultiAssignmentTest, ThrowsOnResultCountMismatchTooMany)
{
    // We expect 3 variables but capitalize_expense only returns 2.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a", "b", "c"],
        "per_trial_steps": [{"type": "multi_execution_assignment", "line": 42, "result_indices": [0, 1, 2], "function": "capitalize_expense",
            "args": [{"type": "scalar_literal", "value": 1}, {"type": "vector_literal", "value": [1]}, {"type": "scalar_literal", "value": 1}]
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
        EXPECT_EQ(e.line(), 42);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("returned 2 values, but 3 were expected"));
    }
}

TEST_F(MultiAssignmentTest, ThrowsOnResultCountMismatchTooFew)
{
    // We expect 1 variable but capitalize_expense returns 2.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a"],
        "per_trial_steps": [{"type": "multi_execution_assignment", "line": 42, "result_indices": [0], "function": "capitalize_expense",
            "args": [{"type": "scalar_literal", "value": 1}, {"type": "vector_literal", "value": [1]}, {"type": "scalar_literal", "value": 1}]
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
        EXPECT_EQ(e.line(), 42);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("returned 2 values, but 1 were expected"));
    }
}

TEST_F(MultiAssignmentTest, ThrowsIfFunctionDoesNotReturnVector)
{
    // We try to multi-assign from 'log', which returns a scalar, not a vector.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a", "b"],
        "per_trial_steps": [{"type": "multi_execution_assignment", "line": 42, "result_indices": [0, 1], "function": "log",
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
        EXPECT_EQ(e.line(), 42);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("did not return a vector for multi-assignment"));
    }
}