#include "test/test_helpers.h"

class BlackScholesTest : public FileCleanupTest
{
};

TEST_F(BlackScholesTest, CallPriceIsCorrect)
{
    // These are standard textbook values for a European call option.
    // The expected price is ~8.02.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["price"],
        "per_trial_steps": [{
            "type": "execution_assignment", "result_indices": [0], "function": "BlackScholes",
            "args": [
                {"type": "scalar_literal", "value": 100.0}, 
                {"type": "scalar_literal", "value": 105.0}, 
                {"type": "scalar_literal", "value": 0.05},  
                {"type": "scalar_literal", "value": 1.0},   
                {"type": "scalar_literal", "value": 0.2},   
                {"type": "string_literal", "value": "call"}
            ]
        }]
    })";
    create_test_recipe("bs_call.json", recipe);
    SimulationEngine engine("bs_call.json");
    auto results = engine.run();
    ASSERT_EQ(results.size(), 1);
    EXPECT_NEAR(std::get<double>(results[0]), 8.02135, 1e-5);
}

TEST_F(BlackScholesTest, PutPriceIsCorrect)
{
    // Using the same parameters, the corresponding put option price is ~7.90.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["price"],
        "per_trial_steps": [{
            "type": "execution_assignment", "result_indices": [0], "function": "BlackScholes",
            "args": [
                {"type": "scalar_literal", "value": 100.0},
                {"type": "scalar_literal", "value": 105.0},
                {"type": "scalar_literal", "value": 0.05},
                {"type": "scalar_literal", "value": 1.0},
                {"type": "scalar_literal", "value": 0.2},
                {"type": "string_literal", "value": "put"}
            ]
        }]
    })";
    create_test_recipe("bs_put.json", recipe);
    SimulationEngine engine("bs_put.json");
    auto results = engine.run();
    ASSERT_EQ(results.size(), 1);
    EXPECT_NEAR(std::get<double>(results[0]), 7.9004, 1e-4);
}

TEST_F(BlackScholesTest, ThrowsOnIncorrectArity)
{
    const std::string recipe = R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["p"],"per_trial_steps":[{"type":"execution_assignment","result_indices":[0],"function":"BlackScholes","args":[]}]})";
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
        EXPECT_THAT(e.what(), ::testing::HasSubstr("requires 6 arguments"));
    }
}

TEST_F(BlackScholesTest, ThrowsOnInvalidOptionType)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["price"],
        "per_trial_steps": [{"type": "execution_assignment", "result_indices": [0], "function": "BlackScholes",
            "args": [
                {"type": "scalar_literal", "value": 100}, {"type": "scalar_literal", "value": 105},
                {"type": "scalar_literal", "value": 0.05}, {"type": "scalar_literal", "value": 1},
                {"type": "scalar_literal", "value": 0.2}, {"type": "string_literal", "value": "invalid_type"}
            ]
        }]
    })";
    create_test_recipe("err.json", recipe);
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception for invalid option type string.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::MismatchedArgumentType);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("Expected 'call' or 'put'"));
    }
}