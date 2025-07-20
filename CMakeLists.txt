# Specify the minimum version of CMake required.
cmake_minimum_required(VERSION 3.10)

# Define the project name.
project(ValuationEngine)

# Set the C++ standard to C++17. This gives us modern features.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Tell CMake where to find our header files (the 'include' directory).
include_directories(include)

# Define the final executable program, naming it "monte-carlo-simulator".
# We start with just main.cpp. We will add more source files later.
add_executable(monte-carlo-simulator
 src/main.cpp
 src/distributions/NormalDistribution.cpp
 src/distributions/PertDistribution.cpp
 src/distributions/UniformDistribution.cpp
 src/distributions/LognormalDistribution.cpp
 src/distributions/TriangularDistribution.cpp
 src/distributions/BernoulliDistribution.cpp
 src/distributions/BetaDistribution.cpp
)