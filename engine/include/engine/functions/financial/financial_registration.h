#pragma once

// This is an INTERNAL header for the financial domain.
// It declares all the individual registration functions that the domain orchestrator needs to call.

class FunctionRegistry;

// Declare the registration function for each operation in this domain.
void register_black_scholes_operation(FunctionRegistry& registry);
// When you add a new function, e.g., BinomialTree.cpp, you will add its declaration here:
// void register_binomial_tree_operation(FunctionRegistry& registry);