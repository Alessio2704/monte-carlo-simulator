#include "include/engine/functions/financial/BlackScholes.h"
#include "include/engine/functions/FunctionRegistry.h"
#include "include/engine/core/EngineException.h"
#include <cmath>

// Local function to register just this operation
void register_black_scholes_operation(FunctionRegistry &registry)
{
    registry.register_function("BlackScholes", []
                               { return std::make_unique<BlackScholesOperation>(); });
}

// --- BlackScholesOperation Implementation ---

// Helper for the Cumulative Normal Distribution Function (CNDF)
// N(x) = 0.5 * erfc(-x / sqrt(2.0))
double cndf(double x)
{
    return 0.5 * std::erfc(-x / std::sqrt(2.0));
}

TrialValue BlackScholesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 5)
    {
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'BlackScholes' requires 5 arguments: spot, strike, rate, time_to_maturity, volatility.");
    }

    // Unpack arguments with clear names
    const double S = std::get<double>(args[0]); // Spot price
    const double K = std::get<double>(args[1]); // Strike price
    const double r = std::get<double>(args[2]); // Risk-free rate
    const double T = std::get<double>(args[3]); // Time to maturity in years
    const double v = std::get<double>(args[4]); // Volatility

    // Input validation for model correctness
    if (S <= 0 || K <= 0 || T <= 0 || v <= 0)
    {
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Black-Scholes inputs (spot, strike, time, volatility) must be positive.");
    }

    // Calculate d1 and d2 parameters
    const double d1 = (std::log(S / K) + (r + (v * v) / 2.0) * T) / (v * std::sqrt(T));
    const double d2 = d1 - v * std::sqrt(T);

    // Calculate the final call option price
    const double call_price = S * cndf(d1) - K * std::exp(-r * T) * cndf(d2);

    return call_price;
}