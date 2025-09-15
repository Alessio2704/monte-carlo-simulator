#include "test/test_helpers.h"

using TestParam = std::tuple<std::string, TrialValue, bool>;

class SimpleOpsEngineTest : public FileCleanupTest,
                            public ::testing::WithParamInterface<TestParam>
{
};

TEST_P(SimpleOpsEngineTest, ExecutesCorrectly)
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
    SimpleOpsEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":123.45}]})", TrialValue(123.45), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["A"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1.0,2.0,3.0]}]})", TrialValue(std::vector<double>{1.0, 2.0, 3.0}), true),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":99.0},{"type":"execution_assignment","result_indices":[1],"function":"identity","args":[{"type":"variable_index","value":0}]}]})", TrialValue(99.0), false)));

// --- Unary Math Operation Tests ---
INSTANTIATE_TEST_SUITE_P(
    UnaryMathTests,
    SimpleOpsEngineTest,
    ::testing::Values(
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"execution_assignment","result_indices":[1],"function":"log","args":[{"type":"scalar_literal","value":10.0}]}]})", TrialValue(std::log(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":10},{"type":"execution_assignment","result_indices":[1],"function":"log10","args":[{"type":"scalar_literal","value":10.0}]}]})", TrialValue(std::log10(10.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":2},{"type":"execution_assignment","result_indices":[1],"function":"exp","args":[{"type":"scalar_literal","value":2.0}]}]})", TrialValue(std::exp(2.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_indices":[1],"function":"sin","args":[{"type":"scalar_literal","value":0.0}]}]})", TrialValue(std::sin(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_indices":[1],"function":"cos","args":[{"type":"scalar_literal","value":0.0}]}]})", TrialValue(std::cos(0.0)), false),
        std::make_tuple(R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","B"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":0},{"type":"execution_assignment","result_indices":[1],"function":"tan","args":[{"type":"scalar_literal","value":0.0}]}]})", TrialValue(std::tan(0.0)), false)));

// --- Fixture and Tests for Arity Errors ---
class SimpleOpsErrorTest : public FileCleanupTest
{
};

#define TEST_ARITY(function_name, json_args, expected_error_msg)                                                                                                                                                                                                                                                                     \
    {                                                                                                                                                                                                                                                                                                                                \
        SCOPED_TRACE("Testing arity for function: " + std::string(function_name));                                                                                                                                                                                                                                                   \
        create_test_recipe("err.json", "{\"simulation_config\":{\"num_trials\":1},\"output_variable_index\":0,\"variable_registry\":[\"X\"],\"per_trial_steps\":[{\"type\":\"execution_assignment\",\"line\":-1,\"result_indices\":[0],\"function\":\"" + std::string(function_name) + "\",\"args\":" + std::string(json_args) + "}]}"); \
        try                                                                                                                                                                                                                                                                                                                          \
        {                                                                                                                                                                                                                                                                                                                            \
            SimulationEngine engine("err.json");                                                                                                                                                                                                                                                                                     \
            engine.run();                                                                                                                                                                                                                                                                                                            \
            FAIL() << "Expected EngineException for function '" << function_name << "', but no exception was thrown.";                                                                                                                                                                                                               \
        }                                                                                                                                                                                                                                                                                                                            \
        catch (const EngineException &e)                                                                                                                                                                                                                                                                                             \
        {                                                                                                                                                                                                                                                                                                                            \
            EXPECT_EQ(e.code(), EngineErrc::IncorrectArgumentCount);                                                                                                                                                                                                                                                                 \
            EXPECT_THAT(e.what(), ::testing::HasSubstr(expected_error_msg));                                                                                                                                                                                                                                                         \
        }                                                                                                                                                                                                                                                                                                                            \
        catch (...)                                                                                                                                                                                                                                                                                                                  \
        {                                                                                                                                                                                                                                                                                                                            \
            FAIL() << "Expected EngineException for function '" << function_name << "', but a different exception was thrown.";                                                                                                                                                                                                      \
        }                                                                                                                                                                                                                                                                                                                            \
    }

TEST_F(SimpleOpsErrorTest, ThrowsOnIncorrectArgCount)
{
    TEST_ARITY("log", "[]", "Function 'log' requires 1 argument.");
    TEST_ARITY("log10", R"([{"type":"scalar_literal","value":1.0},{"type":"scalar_literal","value":2.0}])", "Function 'log10' requires 1 argument.");
    TEST_ARITY("exp", "[]", "Function 'exp' requires 1 argument.");
    TEST_ARITY("sin", R"([{"type":"scalar_literal","value":1.0},{"type":"scalar_literal","value":2.0}])", "Function 'sin' requires 1 argument.");
    TEST_ARITY("cos", "[]", "Function 'cos' requires 1 argument.");
    TEST_ARITY("tan", R"([{"type":"scalar_literal","value":1.0},{"type":"scalar_literal","value":2.0}])", "Function 'tan' requires 1 argument.");
    TEST_ARITY("identity", "[]", "Function 'identity' requires exactly 1 argument.");
}