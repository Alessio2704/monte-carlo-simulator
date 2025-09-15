#include "test/test_helpers.h"

class MultiAssignmentTest : public FileCleanupTest
{
};

// TEST_F(MultiAssignmentTest, CorrectlyUnpacksMixedTypeResult)
// {
//     // Simulates: let assets, amortization, status = capitalize_expense(...)
//     // capitalize_expense now returns a mixed tuple: (double, double, string)
//     // We will test that all three variables get the correct type and value assigned.
//     const std::string recipe = R"({
//         "simulation_config": {"num_trials": 1},
//         "output_variable_index": 0,
//         "variable_registry": ["assets", "amortization", "status", "output_assets", "output_amort", "output_status"],
//         "per_trial_steps": [
//             {
//                 "type": "execution_assignment",
//                 "result_indices": [0, 1, 2],
//                 "function": "capitalize_expense",
//                 "args": [
//                     {"type": "scalar_literal", "value": 100.0},
//                     {"type": "vector_literal", "value": [90.0, 80.0]},
//                     {"type": "scalar_literal", "value": 2.0}
//                 ]
//             },
//             {
//                 "type": "execution_assignment", "result_indices": [3], "function": "identity", "args": [{"type": "variable_index", "value": 0}]
//             },
//             {
//                 "type": "execution_assignment", "result_indices": [4], "function": "identity", "args": [{"type": "variable_index", "value": 1}]
//             },
//             {
//                 "type": "execution_assignment", "result_indices": [5], "function": "identity", "args": [{"type": "variable_index", "value": 2}]
//             }
//         ]
//     })";

//     // Test 1: Check the first variable ('assets')
//     auto recipe1 = nlohmann::json::parse(recipe);
//     recipe1["output_variable_index"] = 3;
//     create_test_recipe("recipe_assets.json", recipe1.dump());
//     SimulationEngine engine_assets("recipe_assets.json");
//     auto results_assets = engine_assets.run();
//     ASSERT_EQ(results_assets.size(), 1);
//     ASSERT_TRUE(std::holds_alternative<double>(results_assets[0]));
//     EXPECT_NEAR(std::get<double>(results_assets[0]), 145.0, 1e-6);

//     // Test 2: Check the second variable ('amortization')
//     auto recipe2 = nlohmann::json::parse(recipe);
//     recipe2["output_variable_index"] = 4;
//     create_test_recipe("recipe_amort.json", recipe2.dump());
//     SimulationEngine engine_amort("recipe_amort.json");
//     auto results_amort = engine_amort.run();
//     ASSERT_EQ(results_amort.size(), 1);
//     ASSERT_TRUE(std::holds_alternative<double>(results_amort[0]));
//     EXPECT_NEAR(std::get<double>(results_amort[0]), 85.0, 1e-6);

//     // Test 3: Check the third variable ('status')
//     auto recipe3 = nlohmann::json::parse(recipe);
//     recipe3["output_variable_index"] = 5;
//     create_test_recipe("recipe_status.json", recipe3.dump());
//     SimulationEngine engine_status("recipe_status.json");
//     auto results_status = engine_status.run();
//     ASSERT_EQ(results_status.size(), 1);
//     ASSERT_TRUE(std::holds_alternative<std::string>(results_status[0]));
//     EXPECT_EQ(std::get<std::string>(results_status[0]), "Success");
// }

TEST_F(MultiAssignmentTest, SingleAssignmentStillWorksWithUnifiedStep)
{
    // let x = add(10, 20)
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["x"],
        "per_trial_steps": [
            {
                "type": "execution_assignment",
                "result_indices": [0],
                "function": "add",
                "args": [
                    {"type": "scalar_literal", "value": 10.0},
                    {"type": "scalar_literal", "value": 20.0}
                ]
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 30.0);
}

TEST_F(MultiAssignmentTest, ThrowsOnResultCountMismatchTooMany)
{
    // We expect 3 variables but capitalize_expense now returns 2.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a", "b", "c"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 42, "result_indices": [0, 1, 2], "function": "capitalize_expense",
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
    // We expect 2 variables but capitalize_expense returns 3.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 42, "result_indices": [0], "function": "capitalize_expense",
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

TEST_F(MultiAssignmentTest, ThrowsWhenSingleAssignmentFunctionReturnsMultipleValues)
{
    // We use a single 'result_indices' but the function returns multiple values.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 42, "result_indices": [0], "function": "capitalize_expense",
            "args": [{"type": "scalar_literal", "value": 1}, {"type": "vector_literal", "value": [1]}, {"type": "scalar_literal", "value": 1}]
        }]
    })";
    create_test_recipe("err.json", recipe);

    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception for multi-return in single assignment context.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::IncorrectArgumentCount);
        EXPECT_EQ(e.line(), 42);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("returned 2 values, but 1 were expected"));
    }
}