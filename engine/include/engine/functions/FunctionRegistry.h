#pragma once

#include "include/engine/core/IExecutable.h"
#include <string>
#include <unordered_map>
#include <functional>
#include <memory>

class FunctionRegistry
{
public:
    using FactoryFunc = std::function<std::unique_ptr<IExecutable>()>;

    void register_function(const std::string &name, FactoryFunc factory);

    const std::unordered_map<std::string, FactoryFunc> &get_factory_map() const;

private:
    std::unordered_map<std::string, FactoryFunc> m_factory_map;
};