//
// Created by liuzikai on 10/5/21.
//

#ifndef _CACHE_H
#define _CACHE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

typedef struct Cache Cache;

typedef enum {
    LRU,
    RANDOM
} Replacement_Policy;

Cache *cache_create(int way_count, int set_count, int block_size_in_bytes, Replacement_Policy policy);

void cache_destroy(Cache *c);

int cache_test(Cache *cache, uint32_t address);

int cache_read_32(Cache *cache, uint32_t address, uint32_t *value_ptr);

int cache_write_32(Cache *cache, uint32_t address, uint32_t value);

#define CACHE_MISS_CYCLE  50

#ifdef __cplusplus
}
#endif

#endif // _CACHE_H
