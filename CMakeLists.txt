# Specify the minimum version of CMake required.
cmake_minimum_required(VERSION 3.14)

set(CMAKE_POLICY_VERSION_MINIMUM 3.5)

# Define the project name.
project(MonteCarloSimulator)

# Set the C++ standard to C++17.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- Add this block to automatically fetch the nlohmann/json library ---
include(FetchContent)
FetchContent_Declare(
  json
  GIT_REPOSITORY https://github.com/nlohmann/json.git
  GIT_TAG "v3.11.2" # Using a specific, stable version is good practice
  SYSTEM
)
FetchContent_MakeAvailable(json)
# --------------------------------------------------------------------

# Tell CMake where to find our own header files.
include_directories(include)

add_executable(monte-carlo-simulator
 src/main.cpp
 src/distributions/NormalDistribution.cpp
 src/distributions/PertDistribution.cpp
 src/distributions/UniformDistribution.cpp
 src/distributions/LognormalDistribution.cpp
 src/distributions/TriangularDistribution.cpp
 src/distributions/BernoulliDistribution.cpp
 src/distributions/BetaDistribution.cpp
 src/engine/SimulationEngine.cpp
)

# --- Add this line to link our executable against the JSON library ---
target_link_libraries(monte-carlo-simulator PRIVATE nlohmann_json::nlohmann_json)
# --------------------------------------------------------------------