cmake_minimum_required(VERSION 3.10)
project(lru_cache)

set(CMAKE_CXX_STANDARD 14)

set(CMAKE_VERBOSE_MAKEFILE OFF)

include_directories("${PROJECT_SOURCE_DIR}/../../harness")
include_directories("${PROJECT_SOURCE_DIR}/../../../../include")  # klee include

add_executable(lru_cache_test lru_cache.c mock_mem.c catch_test.c)