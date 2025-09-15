#pragma once

#include "include/engine/core/IExecutable.h"
#include <string>
#include <unordered_map>
#include <functional>
#include <memory>

// A central registry for all executable functions known to the engine.
class FunctionRegistry
{
public:
    // The type for a factory function that creates an IExecutable instance.
    using FactoryFunc = std::function<std::unique_ptr<IExecutable>()>;

    // Registers a new function with the given name and factory.
    void register_function(const std::string &name, FactoryFunc factory);

    // Returns the complete map of function names to their factories.
    const std::unordered_map<std::string, FactoryFunc> &get_factory_map() const;

private:
    std::unordered_map<std::string, FactoryFunc> m_factory_map;
};