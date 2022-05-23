extern "C" {
#include "cache.h"
#include "cache_private.h"
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

//int get_sign(int x) {
//  if (x == 0)
//     return 0;
//
//  if (x < 0)
//     return -1;
//  else
//     return 1;
//}
//
//int add_by_sign(int x) {
//  if (x == 0)
//     return 0;
//
//  if (x < 0)
//     return x - 1;
//  else
//     return x + 1;
//}

int main()
{
  Cache *c = cache_create(4, 64, 32, LRU);

  uint32_t addr, offset, set_index, tag;
  klee_make_symbolic(&addr, sizeof(addr), "addr");
  klee_assume(addr != 0);

  decode_address(c, addr, &offset, &set_index, &tag);

  klee_watch_obj(&offset, "offset");
  klee_watch_obj(&set_index, "set_index");
  klee_watch_obj(&tag, "tag");

  cache_destroy(c);
}