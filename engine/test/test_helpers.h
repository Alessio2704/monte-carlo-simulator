#pragma once

#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <fstream>
#include <string>
#include <vector>
#include <tuple>
#include <numeric>
#include <cmath>
#include <cstdio>
#include <memory>
#include <array>

#include "include/engine/core/SimulationEngine.h"
#include "include/engine/io/io.h"

// Helper function to create a test recipe file.
inline void create_test_recipe(const std::string &filename, const std::string &content)
{
    std::ofstream test_file(filename);
    test_file << content;
    test_file.close();
}

// Helper to read a file's content into a string
inline std::string read_file_content(const std::string &path)
{
    std::ifstream file(path);
    if (!file.is_open())
    {
        return "ERROR: FILE_NOT_FOUND";
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

// Executes a command and captures its standard output.
inline std::string exec_command(const char *cmd)
{
    std::array<char, 128> buffer;
    std::string result;

#ifdef _WIN32
    // Use the Windows-specific _popen and _pclose functions
    std::unique_ptr<FILE, decltype(&_pclose)> pipe(_popen(cmd, "r"), _pclose);
#else
    // Use the standard POSIX popen and pclose on other systems
    std::unique_ptr<FILE, decltype(&pclose)> pipe(popen(cmd, "r"), pclose);
#endif

    if (!pipe)
    {
        throw std::runtime_error("popen() failed!");
    }
    while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe.get()) != nullptr)
    {
        result += buffer.data();
    }
    return result;
}

// Base fixture for automatic file cleanup, used by all other test fixtures.
class FileCleanupTest : public ::testing::Test
{
protected:
    void SetUp() override
    {
        std::remove("test_output.csv");
        std::remove("recipe.json");
        std::remove("param_test.json");
        std::remove("sampler_test.json");
        std::remove("err.json");
        std::remove("preview_test.json");
        std::remove("test_data.csv");
        std::remove("bad_data.csv");
    }

    void TearDown() override
    {
        std::remove("test_output.csv");
        std::remove("recipe.json");
        std::remove("param_test.json");
        std::remove("sampler_test.json");
        std::remove("err.json");
        std::remove("preview_test.json");
        std::remove("test_data.csv");
        std::remove("bad_data.csv");
    }
};