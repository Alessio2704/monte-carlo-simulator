# This file defines the 'engine_core' library and its tests.
# Paths are relative to this directory (monte-carlo-simulator/engine/).

project(MonteCarloEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- Set Compiler-Specific Warning Flags ---
if(MSVC)
    # Microsoft Visual C++ Compiler
    # /W4 sets a high warning level, /WX treats warnings as errors.
    add_compile_options("/W4" "/WX")
else()
    # GCC and Clang
    add_compile_options("-Wall" "-Wextra" "-Wpedantic" "-Werror=switch")
endif()

# --- Fetch Dependencies ---
include(FetchContent)

FetchContent_Declare(
  json
  GIT_REPOSITORY https://github.com/nlohmann/json.git
  GIT_TAG "v3.12.0" 
)
FetchContent_MakeAvailable(json)

FetchContent_Declare(
  csv
  GIT_REPOSITORY https://github.com/vincentlaucsb/csv-parser.git
  GIT_TAG "2.3.0"
)

FetchContent_MakeAvailable(csv)

# --- Automatically Discover All Engine Source Files ---
# We use file(GLOB_RECURSE) with CONFIGURE_DEPENDS. This modern CMake feature
# automatically detects new .cpp files and re-configures the build when they are
# added or removed, eliminating the need to ever manually edit this file again.

# 1. Find all core source files
file(GLOB_RECURSE ENGINE_CORE_SOURCES
    CONFIGURE_DEPENDS
    "src/engine/core/*.cpp"
    "src/engine/io/*.cpp"
)

# 2. Find all function domain source files
file(GLOB_RECURSE ENGINE_FUNCTION_SOURCES
    CONFIGURE_DEPENDS
    "src/engine/functions/*.cpp" # For the registry
    "src/engine/functions/*/*.cpp" # For all domain implementations
)

# --- Define our Core Library ---
add_library(engine_core STATIC
    # Add all discovered source files to the library
    ${ENGINE_CORE_SOURCES}
    ${ENGINE_FUNCTION_SOURCES}
)


target_include_directories(engine_core PUBLIC
    # For builds, add the 'include' directory from this subdirectory.
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    # For installs, specify the destination.
    $<INSTALL_INTERFACE:include>
)

# Link the engine library against the JSON library.
target_link_libraries(engine_core PUBLIC nlohmann_json::nlohmann_json csv)


# --- Define our Main Executable ---
add_executable(vse
    src/main.cpp
)

# Link the main executable against our core library.
target_link_libraries(vse PRIVATE engine_core)


# --- Testing Configuration ---
# Note: enable_testing() is now in the top-level CMakeLists.txt

# This is CRITICAL for Windows builds. It forces gtest to be built with the
# same dynamic runtime library (/MD or /MDd) as our main project, which prevents
# linker errors. This must be set BEFORE FetchContent_MakeAvailable.
if(MSVC)
  set(gtest_force_shared_crt ON CACHE BOOL "Force shared CRT for gtest on Windows")
endif()

FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG "v1.14.0"
)
FetchContent_MakeAvailable(googletest)
include(GoogleTest)

# Helper macro to reduce boilerplate when adding new test files
macro(add_engine_test test_name)
  add_executable(${test_name} "test/${test_name}.cpp")
  target_link_libraries(${test_name} PRIVATE
      engine_core
      gtest_main
      gmock
  )
  gtest_discover_tests(${test_name})
endmacro()

# Define all our test executables using the macro
add_engine_test(test_operations)
add_engine_test(test_samplers)
add_engine_test(test_errors)
add_engine_test(test_io)
add_engine_test(test_preview)
add_engine_test(test_conditionals)

# Pass the location of the 'vse' executable to the 'test_preview' compile definitions.
# $<TARGET_FILE:vse> is a CMake "generator expression" that resolves to the full path of the executable.
target_compile_definitions(test_preview PRIVATE VSE_EXECUTABLE_PATH="$<TARGET_FILE:vse>")