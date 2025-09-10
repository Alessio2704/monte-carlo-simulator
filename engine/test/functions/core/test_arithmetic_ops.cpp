#include "test/test_helpers.h"

using TestParam = std::tuple<std::string, TrialValue, bool>;

class ArithmeticEngineTest : public FileCleanupTest,
                             public ::testing::WithParamInterface<TestParam>
{
};

TEST_P(ArithmeticEngineTest, ExecutesCorrectly)
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

// --- Binary Math Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    ArithmeticOperationTests,
    ArithmeticEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(30.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"subtract","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(-10.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"multiply","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(200.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":20},{"type":"literal_assignment","result_index":1,"value":10},{"type":"execution_assignment","result_index":2,"function":"divide","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(2.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":2},{"type":"literal_assignment","result_index":1,"value":8},{"type":"execution_assignment","result_index":2,"function":"power","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(256.0), false)));

// --- Vector and Mixed-Type Math Tests ---
INSTANTIATE_TEST_SUITE_P(
    VectorArithmeticTests,
    ArithmeticEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2,3]},{"type":"literal_assignment","result_index":1,"value":[4,5,6]},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(std::vector<double>{5.0, 7.0, 9.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"add","args":[{"type":"variable_index","value":0},{"type":"scalar_literal","value":5.0}]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"add","args":[{"type":"scalar_literal","value":5.0},{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"subtract","args":[{"type":"variable_index","value":0},{"type":"scalar_literal","value":3.0}]}]})", TrialValue(std::vector<double>{7.0, 17.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"subtract","args":[{"type":"scalar_literal","value":100.0},{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{90.0, 80.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,4,6]},{"type":"execution_assignment","result_index":1,"function":"multiply","args":[{"type":"variable_index","value":0},{"type":"scalar_literal","value":10.0}]}]})", TrialValue(std::vector<double>{20.0, 40.0, 60.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"multiply","args":[{"type":"scalar_literal","value":0.5},{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{5.0, 10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[100,200]},{"type":"execution_assignment","result_index":1,"function":"divide","args":[{"type":"variable_index","value":0},{"type":"scalar_literal","value":10.0}]}]})", TrialValue(std::vector<double>{10.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,4,5]},{"type":"execution_assignment","result_index":1,"function":"divide","args":[{"type":"scalar_literal","value":100.0},{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{50.0, 25.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,3,4]},{"type":"execution_assignment","result_index":1,"function":"power","args":[{"type":"variable_index","value":0},{"type":"scalar_literal","value":2.0}]}]})", TrialValue(std::vector<double>{4.0, 9.0, 16.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2,3]},{"type":"execution_assignment","result_index":1,"function":"power","args":[{"type":"scalar_literal","value":2.0},{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{2.0, 4.0, 8.0}), true)));

// --- Nested Expression Test ---
INSTANTIATE_TEST_SUITE_P(
    NestedArithmeticTest,
    ArithmeticEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["A","B","C","D"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"literal_assignment","result_index":2,"value":5},{"type":"execution_assignment","result_index":3,"function":"multiply","args":[{"type":"variable_index","value":0},{"type":"execution_assignment","function":"subtract","args":[{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]}]})", TrialValue(150.0), false)));

class ArithmeticErrorTest : public FileCleanupTest
{
};

TEST_F(ArithmeticErrorTest, ThrowsOnDivisionByZero)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100},{"type":"literal_assignment","result_index":1,"value":0},{"type":"execution_assignment","result_index":2,"function":"divide","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})");
    SimulationEngine engine("err.json");
    try
    {
        engine.run();
        FAIL() << "Expected exception for division by zero.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::DivisionByZero);
    }
}

TEST_F(ArithmeticErrorTest, ThrowsOnVectorSizeMismatch)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2]},{"type":"literal_assignment","result_index":1,"value":[1,2,3]},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})");
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected EngineException for vector size mismatch, but no exception was thrown.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::VectorSizeMismatch);
        EXPECT_THAT(e.what(), ::testing::HasSubstr("Vector size mismatch"));
    }
    catch (...)
    {
        FAIL() << "Expected EngineException for vector size mismatch, but a different exception was thrown.";
    }
}