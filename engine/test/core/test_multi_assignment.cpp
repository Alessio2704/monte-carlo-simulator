#include "test/test_helpers.h"

class MultiAssignmentTest : public FileCleanupTest
{
};

TEST_F(MultiAssignmentTest, SingleAssignmentStillWorksWithUnifiedStep)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["x"],
        "per_trial_steps": [
            {
                "type": "execution_assignment",
                "result": [0],
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
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a", "b", "c"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 42, "result": [0, 1, 2], "function": "capitalize_expense",
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
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 42, "result": [0], "function": "capitalize_expense",
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
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["a"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 42, "result": [0], "function": "capitalize_expense",
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