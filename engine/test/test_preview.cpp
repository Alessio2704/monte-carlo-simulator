#include "test_helpers.h"
#include <nlohmann/json.hpp>

// This macro will be defined by CMake via target_compile_definitions
#ifndef VSE_EXECUTABLE_PATH
#error "VSE_EXECUTABLE_PATH is not defined! Check engine/CMakeLists.txt"
#endif

class EnginePreviewModeTest : public FileCleanupTest
{
};

TEST_F(EnginePreviewModeTest, OutputsCorrectJsonForDeterministicScalar)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry":["a"],
        "per_trial_steps": [{"type": "literal_assignment", "result_index": 0, "value": 123.45678}]
    })";
    create_test_recipe("preview_test.json", recipe);

    // Use the path provided by the build system instead of a hardcoded relative path.
    std::string command = std::string(VSE_EXECUTABLE_PATH) + " --preview preview_test.json";

    std::string output = exec_command(command.c_str());

    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "success");
    EXPECT_EQ(json_out["type"], "scalar");
    EXPECT_NEAR(json_out["value"], 123.4568, 1e-5);
}

TEST_F(EnginePreviewModeTest, OutputsCorrectJsonForStochasticScalar)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 100}, "output_variable_index": 0, "variable_registry":["a"],
        "per_trial_steps": [{"type": "execution_assignment", "result_index": 0, "function": "Normal", "args": [100, 0]}]
    })";
    create_test_recipe("preview_test.json", recipe);

    std::string command = std::string(VSE_EXECUTABLE_PATH) + " --preview preview_test.json";

    std::string output = exec_command(command.c_str());

    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "success");
    EXPECT_EQ(json_out["type"], "scalar");
    EXPECT_NEAR(json_out["value"], 100.0, 1e-5);
}

TEST_F(EnginePreviewModeTest, OutputsCorrectJsonForVector)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry":["a"],
        "per_trial_steps": [{"type": "literal_assignment", "result_index": 0, "value": [1.11111, 2.22222, 3.33333]}]
    })";
    create_test_recipe("preview_test.json", recipe);

    std::string command = std::string(VSE_EXECUTABLE_PATH) + " --preview preview_test.json";

    std::string output = exec_command(command.c_str());

    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "success");
    EXPECT_EQ(json_out["type"], "vector");
    ASSERT_EQ(json_out["value"].size(), 3);
    EXPECT_NEAR(json_out["value"][0], 1.1111, 1e-5);
    EXPECT_NEAR(json_out["value"][1], 2.2222, 1e-5);
    EXPECT_NEAR(json_out["value"][2], 3.3333, 1e-5);
}

TEST_F(EnginePreviewModeTest, OutputsErrorJsonOnRuntimeError)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry":["a"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 42, "result_index": 0, "function": "divide", "args": [1, 0]}]
    })";
    create_test_recipe("preview_test.json", recipe);

    std::string command = std::string(VSE_EXECUTABLE_PATH) + " --preview preview_test.json 2>&1";

    std::string output = exec_command(command.c_str());

    auto json_out = nlohmann::json::parse(output);
    EXPECT_EQ(json_out["status"], "error");
    ASSERT_TRUE(json_out.contains("message"));
    EXPECT_THAT(json_out["message"].get<std::string>(), ::testing::HasSubstr("L42: In function 'divide': Division by zero"));
}