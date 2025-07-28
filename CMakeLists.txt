# Set a modern CMake version
cmake_minimum_required(VERSION 3.14)

project(MonteCarloSimulator)

# Set explicit output directories for binaries and libraries
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
# This is still needed for our own engine headers
include_directories(include)


# --- REFACTORED: Define our Core Library ---
# The library is now much simpler, as most logic is header-only.
# It only contains the implementation of the SimulationEngine.
add_library(engine_core STATIC
    src/engine/SimulationEngine.cpp 
    src/engine/io.cpp
)

# Tell our core library that it needs to link against the JSON library.
# PUBLIC here means that any target that links against engine_core will also
# automatically get the include directories from nlohmann_json.
target_link_libraries(engine_core PUBLIC nlohmann_json::nlohmann_json)


# --- Define our Main Executable ---
# This part is unchanged.
add_executable(monte-carlo-simulator
    src/main.cpp
)

# Link the main executable against our core library
target_link_libraries(monte-carlo-simulator PRIVATE engine_core)


# --- Testing Configuration ---
enable_testing()

FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG "v1.14.0"
)
FetchContent_MakeAvailable(googletest)

# --- REFACTORED: Define our test executable ---
# We have removed the old distributions_tests.cpp as it is no longer valid.
add_executable(run_tests
    test/engine_tests.cpp
)

# Link the test executable against our core library and GoogleTest
target_link_libraries(run_tests PRIVATE
    engine_core
    gtest_main
)

include(GoogleTest)
gtest_discover_tests(run_tests)