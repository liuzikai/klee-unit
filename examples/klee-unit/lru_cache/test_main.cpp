//
// Created by liuzikai on 10/5/21.
//

#include "CppUTest/TestHarness_c.h"
#include "CppUTest/CommandLineTestRunner.h"
#include "CppUTest/TestRegistry.h"
#include "CppUTestExt/MockSupportPlugin.h"

TEST_GROUP_C_WRAPPER(cache_test) {};
TEST_C_WRAPPER(cache_test, create)
TEST_C_WRAPPER(cache_test, decode_encode_address)
TEST_C_WRAPPER(cache_test, move_block_to_front)
TEST_C_WRAPPER(cache_test, simple_read_miss)
TEST_C_WRAPPER(cache_test, simple_read_hit)
TEST_C_WRAPPER(cache_test, read_same_block)
TEST_C_WRAPPER(cache_test, read_test_2_ways)
TEST_C_WRAPPER(cache_test, read_test_4_ways)
TEST_C_WRAPPER(cache_test, write_test_2_ways)
TEST_C_WRAPPER(cache_test, write_test_4_ways)

MockSupportPlugin mockPlugin;

int main(int ac, char** av) {
    TestRegistry::getCurrentRegistry()->installPlugin(&mockPlugin);
    return CommandLineTestRunner::RunAllTests(ac, av);
}