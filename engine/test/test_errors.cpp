#include "test_helpers.h"

class EngineErrorTests : public FileCleanupTest
{
};

TEST_F(EngineErrorTests, ThrowsOnDeleteElementIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable_index":1,
        "variable_registry": ["my_vec", "A"],
        "per_trial_steps": [
            {"type":"literal_assignment","result_index":0,"value":[10.0, 20.0, 30.0]},
            {"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index", "value":0}, 5.0]}
        ]
    })");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnDeleteElementEmptyVector)
{
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials":1}, "output_variable_index":1,
        "variable_registry": ["empty_vec", "A"],
        "per_trial_steps": [
            {"type":"literal_assignment","result_index":0,"value":[]},
            {"type":"execution_assignment","result_index":1,"function":"delete_element","args":[{"type":"variable_index", "value":0}, 0.0]}
        ]
    })");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnDivisionByZero)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":100},{"type":"literal_assignment","result_index":1,"value":0},{"type":"execution_assignment","result_index":2,"function":"divide","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnVectorSizeMismatch)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":2,"variable_registry":["A","B","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[1,2]},{"type":"literal_assignment","result_index":1,"value":[1,2,3]},{"type":"execution_assignment","result_index":2,"function":"add","args":[{"type":"variable_index","value":0},{"type":"variable_index","value":1}]}]})");
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected std::runtime_error for vector size mismatch, but no exception was thrown.";
    }
    catch (const std::runtime_error &e)
    {
        EXPECT_THAT(e.what(), ::testing::HasSubstr("Vector size mismatch"));
    }
    catch (...)
    {
        FAIL() << "Expected std::runtime_error for vector size mismatch, but a different exception was thrown.";
    }
}

TEST_F(EngineErrorTests, ThrowsOnIndexOutOfBounds)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":1,"variable_registry":["A","C"],"per_trial_steps":[{"type":"literal_assignment","result_index":0,"value":[10,20]},{"type":"execution_assignment","result_index":1,"function":"get_element","args":[{"type":"variable_index","value":0},5.0]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnInvalidPertParams)
{
    create_test_recipe("err.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["X"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"Pert","args":[100,50,200]}]})");
    SimulationEngine engine("err.json");
    ASSERT_THROW(engine.run(), std::runtime_error);
}

#define TEST_ARITY(function_name, json_args, expected_error_msg)                                                                                                                                                                                                                                                                     \
    {                                                                                                                                                                                                                                                                                                                                \
        SCOPED_TRACE("Testing arity for function: " + std::string(function_name));                                                                                                                                                                                                                                                   \
        create_test_recipe("err.json", "{\"simulation_config\":{\"num_trials\":1},\"output_variable_index\":0,\"variable_registry\":[\"X\"],\"per_trial_steps\":[{\"type\":\"execution_assignment\",\"line\":-1,\"result_index\":0,\"function\":\"" + std::string(function_name) + "\",\"args\":" + std::string(json_args) + "}]}"); \
        try                                                                                                                                                                                                                                                                                                                          \
        {                                                                                                                                                                                                                                                                                                                            \
            SimulationEngine engine("err.json");                                                                                                                                                                                                                                                                                     \
            engine.run();                                                                                                                                                                                                                                                                                                            \
            FAIL() << "Expected std::runtime_error for function '" << function_name << "', but no exception was thrown.";                                                                                                                                                                                                            \
        }                                                                                                                                                                                                                                                                                                                            \
        catch (const std::runtime_error &e)                                                                                                                                                                                                                                                                                          \
        {                                                                                                                                                                                                                                                                                                                            \
            EXPECT_THAT(e.what(), ::testing::HasSubstr(expected_error_msg));                                                                                                                                                                                                                                                         \
        }                                                                                                                                                                                                                                                                                                                            \
        catch (...)                                                                                                                                                                                                                                                                                                                  \
        {                                                                                                                                                                                                                                                                                                                            \
            FAIL() << "Expected std::runtime_error for function '" << function_name << "', but a different exception was thrown.";                                                                                                                                                                                                   \
        }                                                                                                                                                                                                                                                                                                                            \
    }

TEST_F(EngineErrorTests, AllSamplersThrowOnIncorrectArgCount)
{
    TEST_ARITY("Normal", "[1.0]", "Function 'Normal' requires 2 arguments");
    TEST_ARITY("Uniform", "[1.0, 2.0, 3.0]", "Function 'Uniform' requires 2 arguments");
    TEST_ARITY("Bernoulli", "[]", "Function 'Bernoulli' requires 1 argument");
    TEST_ARITY("Lognormal", "[1.0]", "Function 'Lognormal' requires 2 arguments");
    TEST_ARITY("Beta", "[1.0]", "Function 'Beta' requires 2 arguments");
    TEST_ARITY("Pert", "[1.0, 2.0]", "Function 'Pert' requires 3 arguments");
    TEST_ARITY("Triangular", "[1.0, 2.0, 3.0, 4.0]", "Function 'Triangular' requires 3 arguments");
}

TEST_F(EngineErrorTests, AllOperationsThrowOnIncorrectArgCount)
{
    TEST_ARITY("log", "[]", "Function 'log' requires 1 argument.");
    TEST_ARITY("log10", "[1.0, 2.0]", "Function 'log10' requires 1 argument.");
    TEST_ARITY("exp", "[]", "Function 'exp' requires 1 argument.");
    TEST_ARITY("sin", "[1.0, 2.0]", "Function 'sin' requires 1 argument.");
    TEST_ARITY("cos", "[]", "Function 'cos' requires 1 argument.");
    TEST_ARITY("tan", "[1.0, 2.0]", "Function 'tan' requires 1 argument.");
    TEST_ARITY("identity", "[]", "Function 'identity' requires exactly 1 argument.");
    TEST_ARITY("sum_series", "[[1,2], [3,4]]", "Function 'sum_series' requires 1 argument.");
    TEST_ARITY("series_delta", "[]", "Function 'series_delta' requires 1 argument.");
    TEST_ARITY("compound_series", "[1.0]", "Function 'compound_series' requires 2 arguments.");
    TEST_ARITY("npv", "[0.05, [1,2], 3.0]", "Function 'npv' requires 2 arguments.");
    TEST_ARITY("get_element", "[1]", "Function 'get_element' requires 2 arguments.");
    TEST_ARITY("delete_element", "[[1,2]]", "Function 'delete_element' requires 2 arguments.");
    TEST_ARITY("read_csv_vector", R"([{"type": "string_literal", "value": "f.csv"}])", "Function 'read_csv_vector' requires 2 arguments.");
    TEST_ARITY("grow_series", "[1, 0.1]", "Function 'grow_series' requires 3 arguments.");
    TEST_ARITY("interpolate_series", "[1, 10, 5, 4]", "Function 'interpolate_series' requires 3 arguments.");
    TEST_ARITY("capitalize_expense", "[1, [2,3]]", "Function 'capitalize_expense' requires 3 arguments.");
    TEST_ARITY("read_csv_scalar", R"([{"type": "string_literal", "value": "f.csv"}, {"type": "string_literal", "value": "c"}])", "Function 'read_csv_scalar' requires 3 arguments.");
}

TEST_F(EngineErrorTests, ThrowsOnOutputVariableIndexOutOfBounds)
{
    // The variable registry only has 2 slots (0 and 1), but we ask for slot 5.
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 5, 
        "variable_registry": ["A", "B"], 
        "per_trial_steps": []
    })");

    // The error should happen during construction/parsing, not during run().
    ASSERT_THROW(SimulationEngine engine("err.json"), std::runtime_error);
}

TEST_F(EngineErrorTests, ThrowsOnStepVariableIndexOutOfBounds)
{
    // The registry has one slot (0), but a step tries to access slot 1.
    create_test_recipe("err.json", R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [
            {"type": "execution_assignment", "result_index": 0, "function": "identity", "args": [
                {"type": "variable_index", "value": 1}
            ]}
        ]
    })");
    
    SimulationEngine engine("err.json"); 
    ASSERT_THROW(engine.run(), std::runtime_error);
}