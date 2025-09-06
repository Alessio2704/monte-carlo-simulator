#include "test_helpers.h"

using TestParam = std::tuple<std::string, TrialValue, bool>;

class DeterministicEngineTest : public FileCleanupTest,
                                public ::testing::WithParamInterface<TestParam>
{
};

TEST_P(DeterministicEngineTest, ExecutesCorrectly)
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

// --- Basic Assignment Tests ---
INSTANTIATE_TEST_SUITE_P(
    AssignmentTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":123.45}]})", TrialValue(123.45), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]}]})", TrialValue(std::vector<double>{1.0, 2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":99.0},{"type":"execution_assignment","result_index":1,"function":"identity","args":[{"type":"variable_index","value":0}]}]})", TrialValue(99.0), false)));

// --- Binary and Unary Math Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    MathOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(30.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"subtract","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(-10.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"execution_assignment","result_index":2,"function":"multiply","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(200.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":20},{"type":"literal_assignment","result_index":1,"value":10},{"type":"execution_assignment","result_index":2,"function":"divide","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(2.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":2},{"type":"literal_assignment","result_index":1,"value":8},{"type":"execution_assignment","result_index":2,"function":"power","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(256.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"execution_assignment","result_index":1,"function":"log","args":[10.0]}]})", TrialValue(std::log(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"execution_assignment","result_index":1,"function":"log10","args":[10.0]}]})", TrialValue(std::log10(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":2},{"type":"execution_assignment","result_index":1,"function":"exp","args":[2.0]}]})", TrialValue(std::exp(2.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_index":1,"function":"sin","args":[0.0]}]})", TrialValue(std::sin(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_index":1,"function":"cos","args":[0.0]}]})", TrialValue(std::cos(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_index":1,"function":"tan","args":[0.0]}]})", TrialValue(std::tan(0.0)), false)));

// --- Vector and Time-Series Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    VectorOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2,3]},{"type":"literal_assignment","result_index":1,"value":[4,5,6]},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(std::vector<double>{5.0, 7.0, 9.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["C","base","rate"],"per_trial_steps":[{"type":"literal_assignment","result_index":1,"value":100},{"type":"literal_assignment","result_index":2,"value":0.1},{"type":"execution_assignment","result_index":0,"function":"grow_series","args":[{"type":"variable_index","value":1},{"type":"variable_index","value":2},3.0]}]})", TrialValue(std::vector<double>{110.0, 121.0, 133.1}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["base","rates","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100},{"type":"literal_assignment","result_index":1,"value":[0.1,0.2]},{"type":"execution_assignment","result_index":2,"function":"compound_series","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(std::vector<double>{110.0, 132.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["series","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[100,110,125]},{"type":"execution_assignment","result_index":1,"function":"series_delta","args":[{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["series","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,70]},{"type":"execution_assignment","result_index":1,"function":"sum_series","args":[{"type":"variable_index","value":0}]}]})", TrialValue(100.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["start","end","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":50},{"type":"execution_assignment","result_index":2,"function":"interpolate_series","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},5.0]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0, 40.0, 50.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["A","B","C_in","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"literal_assignment","result_index":2,"value":30},{"type":"execution_assignment","result_index":3,"function":"compose_vector","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["current_rd","past_rd","period","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100.0},{"type":"literal_assignment","result_index":1,"value":[90.0,80.0,70.0]},{"type":"literal_assignment","result_index":2,"value":3.0},{"type":"execution_assignment","result_index":3,"function":"capitalize_expense","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]})", TrialValue(std::vector<double>{186.66666666666666, 80.0}), true)));

// --- Nested Expression Test ---
INSTANTIATE_TEST_SUITE_P(
    NestedExpressionTest,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["A","B","C","D"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"literal_assignment","result_index":2,"value":5},{"type":"execution_assignment","result_index":3,"function":"multiply","args":[{"type":"variable_index","value":0},{"type":"execution_assignment","function":"subtract","args":[{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]}]})", TrialValue(150.0), false)));

// --- Mixed-Type Vector Math Tests ---
INSTANTIATE_TEST_SUITE_P(
    MixedTypeVectorMathTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"add","args":[{"type":"variable_index","value":0},5.0]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"add","args":[5.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{15.0, 25.0, 35.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"subtract","args":[{"type":"variable_index","value":0},3.0]}]})", TrialValue(std::vector<double>{7.0, 17.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"subtract","args":[100.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{90.0, 80.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,4,6]},{"type":"execution_assignment","result_index":1,"function":"multiply","args":[{"type":"variable_index","value":0},10.0]}]})", TrialValue(std::vector<double>{20.0, 40.0, 60.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,30]},{"type":"execution_assignment","result_index":1,"function":"multiply","args":[0.5,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{5.0, 10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[100,200]},{"type":"execution_assignment","result_index":1,"function":"divide","args":[{"type":"variable_index","value":0},10.0]}]})", TrialValue(std::vector<double>{10.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,4,5]},{"type":"execution_assignment","result_index":1,"function":"divide","args":[100.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{50.0, 25.0, 20.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[2,3,4]},{"type":"execution_assignment","result_index":1,"function":"power","args":[{"type":"variable_index","value":0},2.0]}]})", TrialValue(std::vector<double>{4.0, 9.0, 16.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2,3]},{"type":"execution_assignment","result_index":1,"function":"power","args":[2.0,{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{2.0, 4.0, 8.0}), true)));

INSTANTIATE_TEST_SUITE_P(
    DeleteElementOperationTests,
    DeterministicEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec", "A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0}, 1.0]}]})", TrialValue(std::vector<double>{1.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec", "A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0}, 0.0]}]})", TrialValue(std::vector<double>{2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec", "A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0}, 2.0]}]})", TrialValue(std::vector<double>{1.0, 2.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec", "A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index","value":0}, -1.0]}]})", TrialValue(std::vector<double>{1.0, 2.0}), true)));