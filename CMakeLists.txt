# Set a modern CMake version for the entire project
cmake_minimum_required(VERSION 3.14)

# Define the project
project(ValuaScriptProject)

# Set global output directories for a clean build structure.
# All binaries will go to 'build/bin', all libraries to 'build/lib'.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

# Tell CMake to descend into the 'engine' directory and process its CMakeLists.txt.
add_subdirectory(engine)