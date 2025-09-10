#pragma once

// Forward declare the FunctionRegistry to avoid including its full header.
// This is a best practice that further reduces dependencies.
class FunctionRegistry;

// This header ONLY DECLARES the registration function for the financial domain.
void register_financial_functions(FunctionRegistry &registry);