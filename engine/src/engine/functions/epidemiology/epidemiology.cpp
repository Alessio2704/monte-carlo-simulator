#include "include/engine/functions/epidemiology/epidemiology.h"
#include "include/engine/functions/epidemiology/epidemiology_registration.h"
#include "include/engine/functions/FunctionRegistry.h"

// --- Domain Orchestrator ---
// This function implements the public declaration from epidemiology.h.
// Its only job is to call all the private registration functions for this domain.
void register_epidemiology_functions(FunctionRegistry &registry)
{
    register_sir_model_operation(registry);
}