extern "C" {
#include "cache.h"
#include "cache_private.h"
#include "mock_mem.h"
}

#include "klee/klee.h"
#include <assert.h>

#define CATCH_CONFIG_MAIN
#include "catch.hpp"

#include <iostream>

TEST_CASE("decode_encode_address") {

    uint32_t offset, set_index, tag;

    Cache *c = cache_create(4, 64, 32, LRU);

    decode_address(c, 0x12345678, &offset, &set_index, &tag);
    REQUIRE(0b110 == offset);
    REQUIRE(0b110011 == set_index);
    REQUIRE(0b100100011010001010 == tag);
    REQUIRE(0x12345678 == encode_address(c, offset, set_index, tag));

    cache_destroy(c);
}

static void expect_mem_reads(const Cache *c, uint32_t address, const uint32_t *mem_val) {
  for (uint32_t i = 0; i < c->block_size_in_words; i++) {

//    mock_c()->expectOneCall("mem_read_32")
//        ->withUnsignedIntParameters("address", (address & ~c->offset_mask) + (i << 2))
//        ->andReturnUnsignedIntValue(mem_val[i]);
  }
}

//static void test_read_miss(Cache *c, uint32_t address, const uint32_t mem_val[], uint32_t expected_val) {
//  expect_mem_reads(c, address, mem_val);
//
//  uint32_t val;
//  CHECK_EQUAL_C_INT(CACHE_MISS_CYCLE, cache_read_32(c, address, &val));
//  CHECK_EQUAL_C_UINT(expected_val, val);
//
//  mock_c()->checkExpectations();
//  mock_c()->clear();
//}
//
//static void test_read_hit(Cache *c, uint32_t address, uint32_t expected_val) {
//  uint32_t val;
//  CHECK_EQUAL_C_INT(0, cache_read_32(c, address, &val));
//  CHECK_EQUAL_C_UINT(expected_val, val);
//}

int main()
{
  Cache *c = cache_create(4, 64, 32, LRU);

//  uint32_t addr, offset, set_index, tag;
//  klee_make_symbolic(&addr, sizeof(addr), "addr");
//  klee_assume(addr != 0);
//
//  decode_address(c, addr, &offset, &set_index, &tag);
//
//  klee_watch_obj(&offset, "offset");
//  klee_watch_obj(&set_index, "set_index");
//  klee_watch_obj(&tag, "tag");

  uint32_t addr;
  uint32_t val;
  int ret;
  klee_make_symbolic(&addr, sizeof(addr), "addr");
  klee_assume((addr & 0x7FF) == 0);
//  klee_make_symbolic(&val, sizeof(val), "val");
  ret = cache_read_32(c, addr, &val);

  uint32_t addr2;
  klee_make_symbolic(&addr2, sizeof(addr2), "addr2");
  klee_assume((addr2 & 0x7FF) == 0);
  int ret2;
  ret2 = cache_read_32(c, addr2, &val);

  klee_watch_obj(&ret, "ret");
  klee_watch_obj(&ret2, "ret2");
  klee_watch_obj(&actual_read_count, "actual_read_count");

  cache_destroy(c);
}