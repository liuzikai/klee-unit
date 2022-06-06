#include "lru_cache.h"
#include "cache_private.h"
#include "mock_mem.h"

void reset_mock_mem() {
    expected_read_count = 0;
    for (int i = 0; i < RECORD_COUNT; i++) {
        expected_read_ret[expected_read_count] = expected_read_count + 0x10000;
        expected_read_count++;
    }
    actual_read_count = 0;
}

void klee_unit_test_cache_read_32()
{
  reset_mock_mem();

  Cache *cache = cache_create(4, 64, 32, LRU);
  uint32_t address = SYMBOLIC(uint32_t);
  uint32_t value_ptr;
  LET((address & 0x7FF) == 0);
  int ret = cache_read_32(cache, address, &value_ptr);
  WATCH(ret);
  WATCH(value_ptr);

  uint32_t address2 = SYMBOLIC(uint32_t);
  uint32_t value_ptr2;
  LET((address2 & 0x7FF) == 0);
  int ret2 = cache_read_32(cache, address2, &value_ptr2);
  WATCH(ret2);
  WATCH(value_ptr2);

  WATCH(actual_read_count);

  cache_destroy(cache);
}

