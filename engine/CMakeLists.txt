project(ValuaScriptEngine)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(MSVC)
    add_compile_options("/W4" "/WX")
else()
    add_compile_options("-Wall" "-Wextra" "-Wpedantic" "-Werror=switch")
endif()

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

file(GLOB_RECURSE ENGINE_CORE_SOURCES
    CONFIGURE_DEPENDS
    "src/engine/core/*.cpp"
    "src/engine/io/*.cpp"
)

file(GLOB_RECURSE ENGINE_FUNCTION_SOURCES
    CONFIGURE_DEPENDS
    "src/engine/functions/*.cpp"
    "src/engine/functions/*/*.cpp"
)

add_library(engine_core STATIC
    ${ENGINE_CORE_SOURCES}
    ${ENGINE_FUNCTION_SOURCES}
)

target_include_directories(engine_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

target_link_libraries(engine_core PUBLIC nlohmann_json::nlohmann_json csv)

add_executable(vse
    src/main.cpp
)

target_link_libraries(vse PRIVATE engine_core)

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

macro(add_engine_test test_path_and_name)
  get_filename_component(test_name ${test_path_and_name} NAME_WE)
  add_executable(${test_name} "test/${test_path_and_name}.cpp")
  target_link_libraries(${test_name} PRIVATE
      engine_core
      gtest_main
      gmock
  )
  gtest_discover_tests(${test_name})
endmacro()


add_engine_test(core/test_errors)
add_engine_test(core/test_preview)
add_engine_test(core/test_output_writer)
add_engine_test(core/test_multi_assignment)

add_engine_test(functions/core/test_arithmetic_ops)
add_engine_test(functions/core/test_simple_ops)
add_engine_test(functions/core/test_conditionals)
add_engine_test(functions/series/test_series_ops)
add_engine_test(functions/statistics/test_samplers)
add_engine_test(functions/io/test_io_ops)
add_engine_test(functions/financial/test_black_scholes)
add_engine_test(functions/epidemiology/test_sir_model)

target_compile_definitions(test_preview PRIVATE VSE_EXECUTABLE_PATH="$<TARGET_FILE:vse>")