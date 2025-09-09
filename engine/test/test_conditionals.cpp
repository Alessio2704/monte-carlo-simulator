#include "test_helpers.h"

class ConditionalLogicTests : public FileCleanupTest
{
};

// ============================================================================
// == 1. VALID CONDITIONAL EXPRESSIONS
// ============================================================================

TEST_F(ConditionalLogicTests, SelectsThenBranchOnTrueLiteral)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["x"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {"type": "boolean_literal", "value": true},
            "then_expr": {"type": "scalar_literal", "value": 100},
            "else_expr": {"type": "scalar_literal", "value": 200}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 100.0);
}

TEST_F(ConditionalLogicTests, SelectsElseBranchOnFalseLiteral)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["x"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {"type": "boolean_literal", "value": false},
            "then_expr": {"type": "scalar_literal", "value": 100},
            "else_expr": {"type": "scalar_literal", "value": 200}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 200.0);
}

TEST_F(ConditionalLogicTests, HandlesComparisonInCondition)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["x"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {
                "type": "execution_assignment", "function": "__gt__",
                "args": [{"type": "scalar_literal", "value": 50}, {"type": "scalar_literal", "value": 10}]
            },
            "then_expr": {"type": "scalar_literal", "value": 1},
            "else_expr": {"type": "scalar_literal", "value": 0}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 1.0);
}

TEST_F(ConditionalLogicTests, HandlesLogicalOperatorInCondition)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["x"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {
                "type": "execution_assignment", "function": "__and__",
                "args": [{"type": "boolean_literal", "value": true}, {"type": "boolean_literal", "value": false}]
            },
            "then_expr": {"type": "scalar_literal", "value": 100},
            "else_expr": {"type": "scalar_literal", "value": 200}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 200.0);
}

TEST_F(ConditionalLogicTests, CorrectlyReturnsVectorsFromBranches)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["x"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {"type": "boolean_literal", "value": true},
            "then_expr": {"type": "vector_literal", "value": [1, 2, 3]},
            "else_expr": {"type": "vector_literal", "value": [4, 5, 6]}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_TRUE(std::holds_alternative<std::vector<double>>(results[0]));
    const auto &vec = std::get<std::vector<double>>(results[0]);
    EXPECT_EQ(vec, (std::vector<double>{1, 2, 3}));
}

TEST_F(ConditionalLogicTests, HandlesSimpleNestedConditional)
{
    // let result = if true then (if false then 1 else 2) else 3
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["result"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {"type": "boolean_literal", "value": true},
            "then_expr": {
                "type": "conditional_expression",
                "condition": {"type": "boolean_literal", "value": false},
                "then_expr": {"type": "scalar_literal", "value": 1},
                "else_expr": {"type": "scalar_literal", "value": 2}
            },
            "else_expr": {"type": "scalar_literal", "value": 3}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 2.0);
}

TEST_F(ConditionalLogicTests, HandlesDeeplyNestedConditionalThatTriggeredBug)
{
    // This mirrors the exact structure from the bug report.
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 2, "variable_registry": ["selector", "a", "result"],
        "pre_trial_steps": [
            {"type": "literal_assignment", "result_index": 0, "value": 3}
        ],
        "per_trial_steps": [
            {"type": "execution_assignment", "result_index": 1, "function": "Normal", "args": [{"type":"scalar_literal", "value": 99}, {"type":"scalar_literal", "value": 0}]},
            {
                "type": "conditional_assignment", "result_index": 2, "line": 5,
                "condition": {"type": "execution_assignment", "function": "__eq__", "args": [{"type": "variable_index", "value": 0}, {"type": "scalar_literal", "value": 1}]},
                "then_expr": {"type": "scalar_literal", "value": 10},
                "else_expr": {
                    "type": "conditional_expression", "line": 6,
                    "condition": {"type": "execution_assignment", "function": "__eq__", "args": [{"type": "variable_index", "value": 0}, {"type": "scalar_literal", "value": 2}]},
                    "then_expr": {"type": "scalar_literal", "value": 20},
                    "else_expr": {
                        "type": "conditional_expression", "line": 7,
                        "condition": {"type": "execution_assignment", "function": "__eq__", "args": [{"type": "variable_index", "value": 0}, {"type": "scalar_literal", "value": 3}]},
                        "then_expr": {
                            "type": "conditional_expression", "line": 8,
                            "condition": {"type": "execution_assignment", "function": "__gt__", "args": [{"type": "variable_index", "value": 0}, {"type": "scalar_literal", "value": 2}]},
                            "then_expr": {
                                "type": "conditional_expression", "line": 9,
                                "condition": {"type": "execution_assignment", "function": "__eq__", "args": [{"type": "execution_assignment", "function": "multiply", "args": [{"type": "variable_index", "value": 0}, {"type": "scalar_literal", "value": 1}]}, {"type": "scalar_literal", "value": 3}]},
                                "then_expr": {"type": "variable_index", "value": 1},
                                "else_expr": {"type": "scalar_literal", "value": 40}
                            },
                            "else_expr": {"type": "scalar_literal", "value": 50}
                        },
                        "else_expr": {"type": "scalar_literal", "value": 60}
                    }
                }
            }
        ]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 99.0);
}

// ============================================================================
// == 2. ALL OPERATORS
// ============================================================================

TEST_F(ConditionalLogicTests, AllComparisonOperatorsWork)
{
    // ==
    create_test_recipe("eq.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__eq__","args":[{"type":"scalar_literal","value":10},{"type":"scalar_literal","value":10}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("eq.json").run()[0]), true);
    // !=
    create_test_recipe("neq.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__neq__","args":[{"type":"scalar_literal","value":10},{"type":"scalar_literal","value":11}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("neq.json").run()[0]), true);
    // >
    create_test_recipe("gt.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__gt__","args":[{"type":"scalar_literal","value":11},{"type":"scalar_literal","value":10}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("gt.json").run()[0]), true);
    // <
    create_test_recipe("lt.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__lt__","args":[{"type":"scalar_literal","value":10},{"type":"scalar_literal","value":11}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("lt.json").run()[0]), true);
    // >=
    create_test_recipe("gte.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__gte__","args":[{"type":"scalar_literal","value":10},{"type":"scalar_literal","value":10}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("gte.json").run()[0]), true);
    // <=
    create_test_recipe("lte.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__lte__","args":[{"type":"scalar_literal","value":10},{"type":"scalar_literal","value":10}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("lte.json").run()[0]), true);
}

TEST_F(ConditionalLogicTests, AllLogicalOperatorsWork)
{
    // AND
    create_test_recipe("and.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__and__","args":[{"type":"boolean_literal","value":true},{"type":"boolean_literal","value":true}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("and.json").run()[0]), true);
    // OR
    create_test_recipe("or.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__or__","args":[{"type":"boolean_literal","value":true},{"type":"boolean_literal","value":false}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("or.json").run()[0]), true);
    // NOT
    create_test_recipe("not.json", R"({"simulation_config":{"num_trials":1},"output_variable_index":0,"variable_registry":["x"],"per_trial_steps":[{"type":"execution_assignment","result_index":0,"function":"__not__","args":[{"type":"boolean_literal","value":false}]}]})");
    ASSERT_EQ(std::get<bool>(SimulationEngine("not.json").run()[0]), true);
}

TEST_F(ConditionalLogicTests, HandlesComplexLogicalPrecedence)
{
    // let result = false or true and not false  --> should be true
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["result"],
        "per_trial_steps": [{
            "type": "execution_assignment", "result_index": 0, "function": "__or__", "args": [
                {"type": "boolean_literal", "value": false},
                {
                    "type": "execution_assignment", "function": "__and__", "args": [
                        {"type": "boolean_literal", "value": true},
                        {
                            "type": "execution_assignment", "function": "__not__", "args": [
                                {"type": "boolean_literal", "value": false}
                            ]
                        }
                    ]
                }
            ]
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<bool>(results[0]), true);
}

// ============================================================================
// == 3. INTEGRATION WITH STOCHASTICITY
// ============================================================================

TEST_F(ConditionalLogicTests, HandlesStochasticCondition)
{
    // let result = if Bernoulli(0.99999) == 1 then 100 else 200
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["result"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {
                "type": "execution_assignment", "function": "__eq__", "args": [
                    {"type": "execution_assignment", "function": "Bernoulli", "args": [{"type":"scalar_literal", "value": 0.99999}]},
                    {"type": "scalar_literal", "value": 1.0}
                ]
            },
            "then_expr": {"type": "scalar_literal", "value": 100},
            "else_expr": {"type": "scalar_literal", "value": 200}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 100.0); // Should almost always be 100
}

TEST_F(ConditionalLogicTests, HandlesStochasticBranch)
{
    // let result = if true then Normal(500, 0) else 10
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["result"],
        "per_trial_steps": [{
            "type": "conditional_assignment", "result_index": 0,
            "condition": {"type": "boolean_literal", "value": true},
            "then_expr": {
                "type": "execution_assignment", "function": "Normal",
                "args": [{"type":"scalar_literal", "value": 500}, {"type":"scalar_literal", "value": 0}]
            },
            "else_expr": {"type": "scalar_literal", "value": 10}
        }]
    })";
    create_test_recipe("recipe.json", recipe);
    SimulationEngine engine("recipe.json");
    auto results = engine.run();
    ASSERT_EQ(std::get<double>(results[0]), 500.0);
}

// ============================================================================
// == 4. ENGINE-LEVEL ERROR HANDLING
// ============================================================================

TEST_F(ConditionalLogicTests, ThrowsIfConditionIsNotBoolean)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["x"],
        "per_trial_steps": [{ "type": "conditional_assignment", "line": 99, "result_index": 0,
            "condition": {"type": "scalar_literal", "value": 123},
            "then_expr": {"type": "scalar_literal", "value": 1}, "else_expr": {"type": "scalar_literal", "value": 0}
        }]
    })";
    create_test_recipe("err.json", recipe);
    SimulationEngine engine("err.json");
    try
    {
        engine.run();
        FAIL() << "Expected runtime_error for non-boolean condition.";
    }
    catch (const std::runtime_error &e)
    {
        EXPECT_THAT(e.what(), ::testing::HasSubstr("L99: In conditional expression: The 'if' condition did not evaluate to a boolean value."));
    }
}

TEST_F(ConditionalLogicTests, ThrowsIfLogicalOperatorGetsNonBoolean)
{
    const std::string recipe = R"({
        "simulation_config": {"num_trials": 1}, "output_variable_index": 0, "variable_registry": ["x"],
        "per_trial_steps": [{"type": "execution_assignment", "line": 5, "result_index": 0, "function": "__and__",
            "args": [{"type":"boolean_literal", "value": true}, {"type":"scalar_literal", "value": 123}]
        }]
    })";
    create_test_recipe("err.json", recipe);
    SimulationEngine engine("err.json");
    try
    {
        engine.run();
        FAIL() << "Expected runtime_error for logical operator type mismatch.";
    }
    catch (const std::runtime_error &e)
    {
        EXPECT_THAT(e.what(), ::testing::HasSubstr("L5: In function '__and__': 'and' operator requires a boolean argument."));
    }
}