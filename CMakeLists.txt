# Set a modern CMake version
cmake_minimum_required(VERSION 3.14)

project(MonteCarloSimulator)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Add compile options for warnings (this is good practice)
add_compile_options("-Wall" "-Wextra" "-Wpedantic" "-Werror=switch")

# --- Fetch Dependencies ---
include(FetchContent)
FetchContent_Declare(
  json
  GIT_REPOSITORY https://github.com/nlohmann/json.git
  GIT_TAG "v3.12.0" 
)
FetchContent_MakeAvailable(json)

# --- Tell CMake where our headers are ---
include_directories(include)


# --- NEW: Define our Core Library ---
# We create a STATIC library that contains all our core logic.
add_library(engine_core STATIC
    # List all the source files that make up the library
    src/engine/SimulationEngine.cpp
    src/distributions/NormalDistribution.cpp
    src/distributions/PertDistribution.cpp
    src/distributions/UniformDistribution.cpp
    src/distributions/LognormalDistribution.cpp
    src/distributions/TriangularDistribution.cpp
    src/distributions/BernoulliDistribution.cpp
    src/distributions/BetaDistribution.cpp
)

# Tell our core library that it needs to link against the JSON library.
# PUBLIC here means that any target that links against engine_core will also
# automatically get the include directories from nlohmann_json.
target_link_libraries(engine_core PUBLIC nlohmann_json::nlohmann_json)


# --- Define our Main Executable ---
# It now only contains main.cpp
add_executable(monte-carlo-simulator
    src/main.cpp
)

# Link the main executable against our core library
target_link_libraries(monte-carlo-simulator PRIVATE engine_core)


# --- NEW SECTION: Testing Configuration ---
enable_testing()

FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG "v1.14.0"
)
FetchContent_MakeAvailable(googletest)

# Define our test executable
add_executable(run_tests
    test/engine_tests.cpp
    test/distributions_tests.cpp
)

# Link the test executable against our core library and GoogleTest
target_link_libraries(run_tests PRIVATE
    engine_core  # <-- This is the fix! Link against the library.
    gtest_main
)

include(GoogleTest)
gtest_discover_tests(run_tests)