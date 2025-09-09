#pragma once

#include "Errors.h"
#include <stdexcept>
#include <string>

class EngineException : public std::runtime_error
{
public:
    // Constructor
    EngineException(EngineErrc code, const std::string &message, int line_num = -1)
        : std::runtime_error(format_message(line_num, message)),
          m_code(code),
          m_line(line_num)
    {
    }

    // Public getters for testing and diagnostics
    EngineErrc code() const noexcept { return m_code; }
    int line() const noexcept { return m_line; }

private:
    EngineErrc m_code;
    int m_line;

    // Helper to format the final message for the user (the `what()`)
    static std::string format_message(int line_num, const std::string &message)
    {
        if (line_num > 0)
        {
            return "L" + std::to_string(line_num) + ": " + message;
        }
        return message;
    }
};