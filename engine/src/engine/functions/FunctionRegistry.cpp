#include "include/engine/functions/FunctionRegistry.h"
#include "include/engine/core/EngineException.h"

void FunctionRegistry::register_function(const std::string &name, FactoryFunc factory)
{
    if (m_factory_map.count(name) > 0)
    {
        throw std::runtime_error("Developer error: Function '" + name + "' is already registered.");
    }
    m_factory_map[name] = std::move(factory);
}

const std::unordered_map<std::string, FunctionRegistry::FactoryFunc> &FunctionRegistry::get_factory_map() const
{
    return m_factory_map;
}