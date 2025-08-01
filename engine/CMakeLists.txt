# This file defines the 'engine_core' library and its tests.
# Paths are relative to this directory (monte-carlo-simulator/engine/).

project(MonteCarloEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- Set Compiler-Specific Warning Flags ---
set(PROJECT_COMPILE_OPTIONS)
if(MSVC)
    # Microsoft Visual C++ Compiler
    list(APPEND PROJECT_COMPILE_OPTIONS "/W4" "/WX")
else()
    # GCC and Clang
    list(APPEND PROJECT_COMPILE_OPTIONS "-Wall" "-Wextra" "-Wpedantic" "-Werror=switch")
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

# --- Define our Core Library ---
add_library(engine_core STATIC
    src/engine/core/SimulationEngine.cpp
    src/engine/io/io.cpp
    src/engine/functions/operations.cpp
    src/engine/functions/samplers.cpp
    src/engine/core/ExecutionSteps.cpp
)

# Apply our strict compile options ONLY to our own target
target_compile_options(engine_core PRIVATE ${PROJECT_COMPILE_OPTIONS})

target_include_directories(engine_core PUBLIC
    # For builds, add the 'include' directory from this subdirectory.
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    # For installs, specify the destination.
    $<INSTALL_INTERFACE:include>
)

# Link the engine library against its dependencies
# Using PUBLIC here propagates the include directories, which is what we want.
target_link_libraries(engine_core PUBLIC nlohmann_json::nlohmann_json csv)

# Mark the include directories from dependencies as SYSTEM directories.
# This tells the compiler to suppress warnings from their headers.
target_include_directories(engine_core SYSTEM
    PUBLIC
        ${json_INCLUDE_DIR}
        ${csv_INCLUDE_DIR}
)

# --- Define our Main Executable ---
add_executable(vse
    src/main.cpp
)

# Link the main executable against our core library.
target_link_libraries(vse PRIVATE engine_core)


# --- Testing Configuration ---
enable_testing()

FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG "v1.14.0"
)
FetchContent_MakeAvailable(googletest)

# Define our test executable.
add_executable(run_tests
    test/engine_tests.cpp
)

# Link the test executable against our core library and GoogleTest.
# Because engine_core's include directories are PUBLIC, run_tests automatically
# knows where to find the engine headers.
target_link_libraries(run_tests PRIVATE
    engine_core
    gtest_main
    gmock
)

include(GoogleTest)
gtest_discover_tests(run_tests)