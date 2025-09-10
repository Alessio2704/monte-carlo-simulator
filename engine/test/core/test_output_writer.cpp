#include "test/test_helpers.h"

class EngineFileOutputTest : public FileCleanupTest
{
};

TEST_F(EngineFileOutputTest, WritesScalarOutputCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {
            "num_trials": 1,
            "output_file": "test_output.csv"
        },
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [
            {"type": "literal_assignment", "result_index": 0, "value": 123.45}
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    std::string output_path = engine.get_output_file_path();
    ASSERT_FALSE(output_path.empty());
    write_results_to_csv(output_path, results);

    std::string file_content = read_file_content(output_path);
    std::string expected_content = "Result\n123.45\n";
    EXPECT_EQ(file_content, expected_content);
}

TEST_F(EngineFileOutputTest, WritesVectorOutputCorrectly)
{
    const std::string recipe_content = R"({
        "simulation_config": {
            "num_trials": 1,
            "output_file": "test_output.csv"
        },
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [
            {"type": "literal_assignment", "result_index": 0, "value": [10.1, 20.2, 30.3]}
        ]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    std::vector<TrialValue> results = engine.run();

    std::string output_path = engine.get_output_file_path();
    ASSERT_FALSE(output_path.empty());
    write_results_to_csv(output_path, results);

    std::string file_content = read_file_content(output_path);
    std::string expected_content = "Period_1,Period_2,Period_3\n10.1,20.2,30.3\n";
    EXPECT_EQ(file_content, expected_content);
}

TEST_F(EngineFileOutputTest, DoesNotWriteFileWhenNotSpecified)
{
    const std::string recipe_content = R"({
        "simulation_config": {"num_trials": 1},
        "output_variable_index": 0,
        "variable_registry": ["A"],
        "per_trial_steps": [{"type": "literal_assignment", "result_index": 0, "value": 10}]
    })";
    create_test_recipe("recipe.json", recipe_content);

    SimulationEngine engine("recipe.json");
    engine.run();

    std::string output_path = engine.get_output_file_path();
    ASSERT_TRUE(output_path.empty());

    std::ifstream file("test_output.csv");
    EXPECT_FALSE(file.good());
}