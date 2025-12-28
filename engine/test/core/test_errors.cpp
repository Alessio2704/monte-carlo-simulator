#include "test/test_helpers.h"

class CoreEngineErrorTest : public FileCleanupTest
{
};

TEST_F(CoreEngineErrorTest, ThrowsOnOutputVariableIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 5, 
        "variable_registry": ["A", "B"], 
        "per_trial_steps": []
    })");
    try
    {
        SimulationEngine engine("err.json");
        FAIL() << "Constructor should have thrown for out-of-bounds output index.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::IndexOutOfBounds);
    }
}

TEST_F(CoreEngineErrorTest, ThrowsOnStepVariableIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [
            {"type": "execution_assignment", "result": [0], "function": "identity", "args": [
                {"type": "variable_index", "value": 1}
            ]}
        ]
    })");

    SimulationEngine engine("err.json");
    try
    {
        engine.run();
        FAIL() << "Expected exception for out-of-bounds variable access in a step.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::IndexOutOfBounds);
    }
    catch (...)
    {
        FAIL() << "Expected EngineException but a different exception was thrown.";
    }
}