#pragma once

// This is an INTERNAL header for the epidemiology domain.
// It declares all the individual registration functions that the domain orchestrator needs to call.

class FunctionRegistry;

// Declare the registration function for each operation in this domain.
void register_sir_model_operation(FunctionRegistry &registry);