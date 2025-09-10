#include "test/test_helpers.h"

// This test fixture sets up the necessary CSV files for testing reading operations.
class CsvEngineTest : public FileCleanupTest
{
protected:
    void SetUp() override
    {
        FileCleanupTest::SetUp();
        std::ofstream csv_file("test_data.csv");
        csv_file << "ID,Value,Rate\n";
        csv_file << "1,100.5,0.05\n";
        csv_file << "2,200.0,0.06\n";
        csv_file << "3,-50.25,0.07\n";
        csv_file.close();

        std::ofstream bad_csv_file("bad_data.csv");
        bad_csv_file << "Header\n";
        bad_csv_file << "NotANumber\n";
        bad_csv_file.close();
    }
};

TEST_F(CsvEngineTest, ReadsVectorCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"} ]
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<std::vector<double>>(results[0]));
    const auto &result_vec = std::get<std::vector<double>>(results[0]);
    const std::vector<double> expected_vec = {100.5, 200.0, -50.25};

    ASSERT_EQ(result_vec.size(), expected_vec.size());
    for (size_t i = 0; i < result_vec.size(); ++i)
    {
        EXPECT_NEAR(result_vec[i], expected_vec[i], 1e-6);
    }
}

TEST_F(CsvEngineTest, ReadsScalarCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result_index": 0, "function": "read_csv_scalar",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Rate"}, {"type":"scalar_literal", "value":2.0} ]
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<double>(results[0]));
    double result_scalar = std::get<double>(results[0]);
    EXPECT_NEAR(result_scalar, 0.07, 1e-6);
}

TEST_F(CsvEngineTest, UsesPreloadedDataInTrial)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 2,
        "variable_registry": ["A", "B", "C"],
        "pre_trial_steps": [
            {
                "type": "execution_assignment", "result_index": 0, "function": "read_csv_scalar",
                "args": [ {"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"}, {"type":"scalar_literal", "value":0} ]
            }
        ],
        "per_trial_steps": [
            {"type": "literal_assignment", "result_index": 1, "value": 10.0},
            {"type": "execution_assignment", "result_index": 2, "function": "add", "args": [{"type":"variable_index", "value":0}, {"type":"variable_index", "value":1}]}
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();
    ASSERT_EQ(results.size(), 1);
    ASSERT_TRUE(std::holds_alternative<double>(results[0]));
    double result_scalar = std::get<double>(results[0]);
    EXPECT_NEAR(result_scalar, 110.5, 1e-6);
}

TEST_F(CsvEngineTest, ThrowsOnFileNotFound)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "non_existent_file.csv"}, {"type": "string_literal", "value": "Value"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::CsvFileNotFound);
    }
}

TEST_F(CsvEngineTest, ThrowsOnColumnNotFound)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "NonExistentColumn"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::CsvColumnNotFound);
    }
}

TEST_F(CsvEngineTest, ThrowsOnRowIndexOutOfBounds)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_scalar",
            "args": [{"type": "string_literal", "value": "test_data.csv"}, {"type": "string_literal", "value": "Value"}, {"type":"scalar_literal", "value":99.0}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::CsvRowIndexOutOfBounds);
    }
}

TEST_F(CsvEngineTest, ThrowsOnNonNumericData)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["A"],
        "pre_trial_steps": [{ "type": "execution_assignment", "result_index": 0, "function": "read_csv_vector",
            "args": [{"type": "string_literal", "value": "bad_data.csv"}, {"type": "string_literal", "value": "Header"}]
        }]
    })";
    create_test_recipe("err.json", recipe_content);
    try
    {
        SimulationEngine engine("err.json");
        engine.run();
        FAIL() << "Expected exception";
    }
    catch (const EngineException &e)
    {
        EXPECT_EQ(e.code(), EngineErrc::CsvConversionError);
    }
}

// This fixture is for tests that do not require pre-made files.
class IoOpsErrorTest : public FileCleanupTest
{
};

#define TEST_ARITY(function_name, json_args, expected_error_msg)                                                                                                                                                                                                                                                                     \
    {                                                                                                                                                                                                                                                                                                                                \
        SCOPED_TRACE("Testing arity for function: " + std::string(function_name));                                                                                                                                                                                                                                                   \
        create_test_recipe("err.json", "{\"simulation_config\":{\"num_trials\":1},\"output_variable_index\":0,\"variable_registry\":[\"X\"],\"per_trial_steps\":[{\"type\":\"execution_assignment\",\"line\":-1,\"result_index\":0,\"function\":\"" + std::string(function_name) + "\",\"args\":" + std::string(json_args) + "}]}"); \
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

TEST_F(IoOpsErrorTest, ThrowsOnIncorrectArgCount)
{
    TEST_ARITY("read_csv_vector", R"([{"type":"string_literal","value":"f.csv"}])", "Function 'read_csv_vector' requires 2 arguments.");
    TEST_ARITY("read_csv_scalar", R"([{"type":"string_literal","value":"f.csv"},{"type":"string_literal","value":"c"}])", "Function 'read_csv_scalar' requires 3 arguments.");
}