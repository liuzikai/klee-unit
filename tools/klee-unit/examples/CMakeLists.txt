add_executable(klee-unit-hello hello.c)
target_include_directories(klee-unit-hello PRIVATE ../include)

add_executable(klee-unit-foo-test foo_test.c)
target_include_directories(klee-unit-foo-test PRIVATE ../include)