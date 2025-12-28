#include "test/test_helpers.h"
#include <numeric>

class SirModelTest : public FileCleanupTest
{
};

TEST_F(SirModelTest, ThrowsOnIncorrectArity)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["s", "i", "r"],
        "per_trial_steps": [{"type": "execution_assignment", "result": [0, 1, 2], "function": "SirModel",
            "args": [{"type": "scalar_literal", "value": 1}]
        }]
    })";
    create_test_recipe("err.json", recipe);

    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception for incorrect argument count.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::IncorrectArgumentCount);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("requires 7 arguments"));
    }
}

TEST_F(SirModelTest, ThrowsOnZeroPopulation)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0,
        "variable_registry": ["s", "i", "r"],
        "per_trial_steps": [{"type": "execution_assignment", "result": [0, 1, 2], "function": "SirModel",
            "args": [
                {"type": "scalar_literal", "value": 0}, {"type": "scalar_literal", "value": 0},
                {"type": "scalar_literal", "value": 0}, {"type": "scalar_literal", "value": 0.2},
                {"type": "scalar_literal", "value": 0.1}, {"type": "scalar_literal", "value": 10},
                {"type": "scalar_literal", "value": 1.0}
            ]
        }]
    })";
    create_test_recipe("err.json", recipe);

    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception for zero population.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::InvalidSamplerParameters);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("Total population in SirModel cannot be zero"));
    }
}

TEST_F(SirModelTest, CorrectlyCalculatesDeterministicModel)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 1,
        "variable_registry": ["susceptible", "infected", "recovered"],
        "per_trial_steps": [{"type": "execution_assignment", "result": [0, 1, 2], "function": "SirModel",
            "args": [
                {"type": "scalar_literal", "value": 999}, {"type": "scalar_literal", "value": 1},
                {"type": "scalar_literal", "value": 0}, {"type": "scalar_literal", "value": 0.3},
                {"type": "scalar_literal", "value": 0.1}, {"type": "scalar_literal", "value": 5},
                {"type": "scalar_literal", "value": 1.0}
            ]
        }]
    })";
    create_test_recipe("recipe.json", recipe);

    // We will check the "infected" vector (output_variable_index: 1)
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<std::vector<double>>(results[0]));

    const auto &infected_vec = std::get<std::vector<double>>(results[0]);
    ASSERT_EQ(infected_vec.size(), 5);

    // Expected values calculated manually for the first few steps
    EXPECT_NEAR(infected_vec[0], 1.0, 1e-2);    // i0
    EXPECT_NEAR(infected_vec[1], 1.1997, 1e-2); // i0 + (beta*s0*i0/N - gamma*i0)*dt
    EXPECT_NEAR(infected_vec[2], 1.4390, 1e-2);
    EXPECT_NEAR(infected_vec[3], 1.7251, 1e-2);
    EXPECT_NEAR(infected_vec[4], 2.0669, 1e-2);
}