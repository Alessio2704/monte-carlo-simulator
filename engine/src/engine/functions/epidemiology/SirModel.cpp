#include "include/engine/functions/epidemiology/SirModel.h"
#include "include/engine/core/IExecutable.h"
#include "include/engine/functions/FunctionRegistry.h"
#include "include/engine/core/EngineException.h"
#include <vector>
#include <numeric>
#include <algorithm>


// Local function to register just this operation
void register_sir_model_operation(FunctionRegistry &registry)
{
    registry.register_function("SirModel", []
                               { return std::make_unique<SirModelOperation>(); });
}

std::vector<TrialValue> SirModelOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 7)
    {
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'SirModel' requires 7 arguments: s0, i0, r0, beta, gamma, periods, dt.");
    }

    const double s0 = std::get<double>(args[0]);
    const double i0 = std::get<double>(args[1]);
    const double r0 = std::get<double>(args[2]);
    const double beta = std::get<double>(args[3]);  // Transmission rate
    const double gamma = std::get<double>(args[4]); // Recovery rate
    const int periods = static_cast<int>(std::get<double>(args[5]));
    const double dt = std::get<double>(args[6]); // Time step (e.g., 1 for 1 day)

    if (periods <= 0)
        return {std::vector<double>{}, std::vector<double>{}, std::vector<double>{}};

    const double N = s0 + i0 + r0; // Total population
    if (N == 0)
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Total population in SirModel cannot be zero.");

    std::vector<double> s(periods), i(periods), r(periods);
    s[0] = s0;
    i[0] = i0;
    r[0] = r0;

    for (int t = 0; t < periods - 1; ++t)
    {
        const double s_t = s[t];
        const double i_t = i[t];

        const double dS = (-beta * s_t * i_t / N) * dt;
        const double dI = (beta * s_t * i_t / N - gamma * i_t) * dt;
        const double dR = (gamma * i_t) * dt;

        s[t + 1] = std::max(0.0, s_t + dS);
        i[t + 1] = std::max(0.0, i_t + dI);
        r[t + 1] = std::max(0.0, r[t] + dR);
    }

    // Return the three vectors as a tuple of TrialValues
    return {TrialValue(s), TrialValue(i), TrialValue(r)};
}