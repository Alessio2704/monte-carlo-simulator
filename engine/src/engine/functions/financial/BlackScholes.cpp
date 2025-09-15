#include "include/engine/functions/financial/BlackScholes.h"
#include "include/engine/functions/FunctionRegistry.h"
#include "include/engine/core/EngineException.h"
#include <cmath>
#include <string>
#include <algorithm>
#include <cctype>

// Local function to register just this operation (unchanged)
void register_black_scholes_operation(FunctionRegistry &registry)
{
    registry.register_function("BlackScholes", []
                               { return std::make_unique<BlackScholesOperation>(); });
}

// --- BlackScholesOperation Implementation ---

// Helper for the Cumulative Normal Distribution Function (CNDF) (unchanged)
double cndf(double x)
{
    return 0.5 * std::erfc(-x / std::sqrt(2.0));
}

TrialValue BlackScholesOperation::execute(const std::vector<TrialValue> &args) const
{
    if (args.size() != 6)
    {
        throw EngineException(EngineErrc::IncorrectArgumentCount, "Function 'BlackScholes' requires 6 arguments: spot, strike, rate, time_to_maturity, volatility, option_type ('call' or 'put').");
    }

    const double S = std::get<double>(args[0]);                   // Spot price
    const double K = std::get<double>(args[1]);                   // Strike price
    const double r = std::get<double>(args[2]);                   // Risk-free rate
    const double T = std::get<double>(args[3]);                   // Time to maturity in years
    const double v = std::get<double>(args[4]);                   // Volatility
    std::string option_type_str = std::get<std::string>(args[5]); // Option type

    // Input validation for model correctness
    if (S <= 0 || K <= 0 || T <= 0 || v <= 0)
    {
        throw EngineException(EngineErrc::InvalidSamplerParameters, "Black-Scholes inputs (spot, strike, time, volatility) must be positive.");
    }

    // Convert option_type to lowercase for case-insensitive comparison
    std::transform(option_type_str.begin(), option_type_str.end(), option_type_str.begin(),
                   [](unsigned char c)
                   { return static_cast<char>(std::tolower(c)); });

    const double d1 = (std::log(S / K) + (r + (v * v) / 2.0) * T) / (v * std::sqrt(T));
    const double d2 = d1 - v * std::sqrt(T);

    if (option_type_str == "call")
    {
        // Calculate the call option price
        const double call_price = S * cndf(d1) - K * std::exp(-r * T) * cndf(d2);
        return call_price;
    }
    else if (option_type_str == "put")
    {
        // Calculate the put option price using the corresponding formula
        const double put_price = K * std::exp(-r * T) * cndf(-d2) - S * cndf(-d1);
        return put_price;
    }
    else
    {
        // Handle invalid option type string
        throw EngineException(EngineErrc::MismatchedArgumentType, "Invalid option_type for BlackScholes. Expected 'call' or 'put', but got '" + option_type_str + "'.");
    }
}