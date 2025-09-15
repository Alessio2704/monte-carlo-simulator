#include "test/test_helpers.h"

using TestParam = std::tuple<std::string, TrialValue, bool>;

class SeriesOpsEngineTest : public FileCleanupTest,
                            public ::testing::WithParamInterface<TestParam>
{
};

TEST_P(SeriesOpsEngineTest, ExecutesCorrectly)
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

// --- Vector and Time-Series Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    VectorOperationTests,
    SeriesOpsEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["C","base","rate"],"per_trial_steps":[{"type":"literal_assignment","result_index":1,"value":100},{"type":"literal_assignment","result_index":2,"value":0.1},{"type":"execution_assignment","result_indices":[0],"function":"grow_series","args":[{"type":"variable_index","value":1},{"type":"variable_index","value":2},{"type":"scalar_literal","value":3.0}]}]})", TrialValue(std::vector<double>{110.0, 121.0, 133.1}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["base","rates","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100},{"type":"literal_assignment","result_index":1,"value":[0.1,0.2]},{"type":"execution_assignment","result_indices":[2],"function":"compound_series","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})", TrialValue(std::vector<double>{110.0, 132.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["series","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[100,110,125]},{"type":"execution_assignment","result_indices":[1],"function":"series_delta","args":[{"type":"variable_index","value":0}]}]})", TrialValue(std::vector<double>{10.0, 15.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["series","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20,70]},{"type":"execution_assignment","result_indices":[1],"function":"sum_series","args":[{"type":"variable_index","value":0}]}]})", TrialValue(100.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["start","end","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":50},{"type":"execution_assignment","result_indices":[2],"function":"interpolate_series","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"scalar_literal","value":5.0}]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0, 40.0, 50.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["A","B","C_in","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"literal_assignment","result_index":1,"value":20},{"type":"literal_assignment","result_index":2,"value":30},{"type":"execution_assignment","result_indices":[3],"function":"compose_vector","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]})", TrialValue(std::vector<double>{10.0, 20.0, 30.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["A", "B", "C_in", "C"],"per_trial_steps":[{"type":"literal_assignment", "result_index":0, "value":5.0},{"type":"literal_assignment", "result_index":1, "value":[10.0, 20.0, 30.0]},{"type":"literal_assignment", "result_index":2, "value":40.0},{"type":"execution_assignment","result_indices":[3],"function":"compose_vector","args":[{"type":"variable_index", "value":0},{"type":"variable_index", "value":1},{"type":"variable_index", "value":2}]}]})", TrialValue(std::vector<double>{5.0, 10.0, 20.0, 30.0, 40.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":3,"variable_registry":["current_rd","past_rd","period","C", "D"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100.0},{"type":"literal_assignment","result_index":1,"value":[90.0,80.0,70.0]},{"type":"literal_assignment","result_index":2,"value":3.0},{"type":"execution_assignment","result_indices":[3, 4],"function":"capitalize_expense","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]})", TrialValue(186.66666666666666), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":4,"variable_registry":["current_rd","past_rd","period","C", "D"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100.0},{"type":"literal_assignment","result_index":1,"value":[90.0,80.0,70.0]},{"type":"literal_assignment","result_index":2,"value":3.0},{"type":"execution_assignment","result_indices":[3, 4],"function":"capitalize_expense","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1},{"type":"variable_index","value":2}]}]})", TrialValue(80.0), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["my_vec", "A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]},{"type":"execution_assignment","result_indices":[1],"function":"delete_element","args":[{"type":"variable_index","value":0}, {"type":"scalar_literal","value":1.0}]}]})", TrialValue(std::vector<double>{1.0, 3.0}), true)));

// --- NEW: Fixture and Tests for Arity and Other Errors ---
class SeriesErrorTest : public FileCleanupTest
{
};

#define TEST_ARITY(function_name, json_args, expected_error_msg)                                                                                                                                                                                                                                                                         \
    {                                                                                                                                                                                                                                                                                                                                    \
        SCOPED_TRACE("Testing arity for function: " + std::string(function_name));                                                                                                                                                                                                                                                       \
        create_test_recipe("err.json", "{\"simulation_config\":{\"num_trials\":1},\"output_variable_index\":0,\"variable_registry\":[\"X\"],\"per_trial_steps\":[{\"type\":\"execution_assignment\",\"line\":-1,\"result_indices\":[0],\"function\":\"" + std::string(function_name) + "\",\"args\":" + std::string(json_args) + "}]}"); \
        try                                                                                                                                                                                                                                                                                                                              \
        {                                                                                                                                                                                                                                                                                                                                \
            SimulationEngine engine("err.json");                                                                                                                                                                                                                                                                                         \
            engine.run();                                                                                                                                                                                                                                                                                                                \
            FAIL() << "Expected EngineException for function '" << function_name << "', but no exception was thrown.";                                                                                                                                                                                                                   \
        }                                                                                                                                                                                                                                                                                                                                \
        catch (const EngineException &e)                                                                                                                                                                                                                                                                                                 \
        {                                                                                                                                                                                                                                                                                                                                \
            EXPECT_EQ(e.code(), EngineErrc::IncorrectArgumentCount);                                                                                                                                                                                                                                                                     \
            EXPECT_THAT(e.what(), ::testing::HasSubstr(expected_error_msg));                                                                                                                                                                                                                                                             \
        }                                                                                                                                                                                                                                                                                                                                \
        catch (...)                                                                                                                                                                                                                                                                                                                      \
        {                                                                                                                                                                                                                                                                                                                                \
            FAIL() << "Expected EngineException for function '" << function_name << "', but a different exception was thrown.";                                                                                                                                                                                                          \
        }                                                                                                                                                                                                                                                                                                                                \
    }

TEST_F(SeriesErrorTest, ThrowsOnIncorrectArgCount)
{
    TEST_ARITY("sum_series", R"([{"type":"vector_literal","value":[1,2]},{"type":"vector_literal","value":[3,4]}])", "Function 'sum_series' requires 1 argument.");
    TEST_ARITY("series_delta", "[]", "Function 'series_delta' requires 1 argument.");
    TEST_ARITY("compound_series", R"([{"type":"scalar_literal","value":1.0}])", "Function 'compound_series' requires 2 arguments.");
    TEST_ARITY("npv", R"([{"type":"scalar_literal","value":0.05},{"type":"vector_literal","value":[1,2]},{"type":"scalar_literal","value":3.0}])", "Function 'npv' requires 2 arguments.");
    TEST_ARITY("get_element", R"([{"type":"scalar_literal","value":1}])", "Function 'get_element' requires 2 arguments.");
    TEST_ARITY("delete_element", R"([{"type":"vector_literal","value":[1,2]}])", "Function 'delete_element' requires 2 arguments.");
    TEST_ARITY("grow_series", R"([{"type":"scalar_literal","value":1},{"type":"scalar_literal","value":0.1}])", "Function 'grow_series' requires 3 arguments.");
    TEST_ARITY("interpolate_series", R"([{"type":"scalar_literal","value":1},{"type":"scalar_literal","value":10},{"type":"scalar_literal","value":5},{"type":"scalar_literal","value":4}])", "Function 'interpolate_series' requires 3 arguments.");
    TEST_ARITY("capitalize_expense", R"([{"type":"scalar_literal","value":1},{"type":"vector_literal","value":[2,3]}])", "Function 'capitalize_expense' requires 3 arguments.");
}

TEST_F(SeriesErrorTest, ThrowsOnGetElementIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_indices":[1],"function":"get_element","args":[{"type":"variable_index","value":0},{"type":"scalar_literal", "value":5.0}]}]})");
    SimulationEngine engine("err.json");
    try
    {
        engine.run();
        FAIL() << "Expected exception for get_element out of bounds.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::IndexOutOfBounds);
    }
}

TEST_F(SeriesErrorTest, ThrowsOnDeleteElementIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable_index":1,
        "variable_registry": ["my_vec", "A"],
        "per_trial_steps": [
            {"type":"literal_assignment","result_index":0,"value":[10.0, 20.0, 30.0]},
            {"type":"execution_assignment","result_indices":[1],"function":"delete_element","args":[{"type":"variable_index", "value":0}, {"type":"scalar_literal", "value":5.0}]}
        ]
    })");
    SimulationEngine engine("err.json");
    try
    {
        engine.run();
        FAIL() << "Expected exception for out-of-bounds delete.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::IndexOutOfBounds);
    }
}

TEST_F(SeriesErrorTest, ThrowsOnDeleteElementEmptyVector)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable_index":1,
        "variable_registry": ["empty_vec", "A"],
        "per_trial_steps": [
            {"type":"literal_assignment","result_index":0,"value":[]},
            {"type":"execution_assignment","result_indices":[1],"function":"delete_element","args":[{"type":"variable_index", "value":0}, {"type":"scalar_literal", "value":0.0}]}
        ]
    })");
    SimulationEngine engine("err.json");
    try
    {
        engine.run();
        FAIL() << "Expected exception for delete on empty vector.";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::EmptyVectorOperation);
    }
}