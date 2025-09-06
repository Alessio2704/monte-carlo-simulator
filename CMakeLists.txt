# Set a modern CMake version for the entire project
cmake_minimum_required(VERSION 3.14)

# Define the project
project(ValuaScriptProject)

# --- Enable Testing for the Entire Project ---
# This MUST be in the top-level CMakeLists.txt for ctest to work correctly.
enable_testing()
include(CTest)

# --- Set MSVC Runtime Library Policy ---
# This is critical for ensuring that our code and all dependencies (like GoogleTest)
# are compiled and linked with the same dynamic runtime library (/MD or /MDd) on Windows.
# This must be set at the top-level CMakeLists.txt before any targets are defined.
if(MSVC)
  set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")
endif()

# Set global output directories for a clean build structure.
# All binaries will go to 'build/bin', all libraries to 'build/lib'.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")

# Tell CMake to descend into the 'engine' directory and process its CMakeLists.txt.
add_subdirectory(engine)