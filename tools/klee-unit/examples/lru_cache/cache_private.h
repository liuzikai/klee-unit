#ifndef _CACHE_PRIVATE_H
#define _CACHE_PRIVATE_H

#include <stdint.h>

typedef struct {
    uint8_t valid;      /* 1 for valid */
    uint8_t dirty;      /* 1 for dirty */
    uint32_t tag;
    uint32_t* data;     /* indexed with offset */
} Cache_Block;

typedef struct {
    Cache_Block* ways;  /* 0 is the most recently used */
} Cache_Set;

struct Cache {
    int way_count;
    int set_count;
    int block_size_in_words;

    Replacement_Policy policy;

    uint32_t offset_mask;
    uint32_t offset_bit_count;
    uint32_t set_index_mask;
    uint32_t set_index_bit_count;

    Cache_Set* sets;
};

void decode_address(Cache *c, uint32_t address, uint32_t *offset, uint32_t *set_index, uint32_t *tag);

uint32_t encode_address(Cache *c, uint32_t offset, uint32_t set_index, uint32_t tag);

void move_block_to_front(Cache_Block *block, Cache_Block *head);

#endif
