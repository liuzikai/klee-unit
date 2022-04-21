install(PROGRAMS klee-unit DESTINATION bin)

# Copy into the build directory's binary directory
#configure_file(klee-unit "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/klee-unit" COPYONLY)
