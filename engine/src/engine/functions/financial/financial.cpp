#include "include/engine/functions/financial/financial.h"
#include "include/engine/functions/financial/financial_registration.h"
#include "include/engine/functions/FunctionRegistry.h"

// --- Domain Orchestrator ---
// This function implements the public declaration from financial.h.
// Its only job is to call all the private registration functions for this domain.
void register_financial_functions(FunctionRegistry &registry)
{
    register_black_scholes_operation(registry);
    // When you add a new function, you will add its registration call here:
    // register_binomial_tree_operation(registry);
}