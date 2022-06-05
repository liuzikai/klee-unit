//
// Created by liuzikai on 10/5/21.
//

#include <stdlib.h>
#include <string.h>
#include "lru_cache.h"
#include "cache_private.h"
#include "shell.h"

Cache *cache_create(int way_count, int set_count, int block_size_in_bytes, Replacement_Policy policy) {
    Cache *c = malloc(sizeof(Cache));

    c->way_count = way_count;
    c->set_count = set_count;
    c->block_size_in_words = block_size_in_bytes / 4;
    c->policy = policy;

    c->offset_mask = ((uint32_t) block_size_in_bytes) - 1U;

    c->offset_bit_count = -1;
    while (block_size_in_bytes) {
        block_size_in_bytes >>= 1;
        c->offset_bit_count++;
    }
    c->set_index_mask = ((uint32_t) set_count) - 1U;

    c->set_index_bit_count = -1;
    while (set_count) {
        set_count >>= 1;
        c->set_index_bit_count++;
    }

    // Use fields in c instead of argument variables as they are invalid now

    c->sets = malloc(sizeof(Cache_Set) * c->set_count);
    for (size_t i = 0; i < c->set_count; i++) {
        c->sets[i].ways = malloc(sizeof(Cache_Block) * c->way_count);
//        memset(c->sets[i].ways, 0, sizeof(Cache_Block) * c->way_count);
        for (size_t j = 0; j < c->way_count; j++) {
          c->sets[i].ways[j].valid = c->sets[i].ways[j].dirty = 0;
          c->sets[i].ways[j].tag = 0;
            c->sets[i].ways[j].data = malloc(sizeof(uint32_t) * c->block_size_in_words);
        }
    }

    return c;
}

void cache_destroy(Cache *c) {
    for (size_t i = 0; i < c->set_count; i++) {
        for (size_t j = 0; j < c->way_count; j++) {
            free(c->sets[i].ways[j].data);
        }
        free(c->sets[i].ways);
    }
    free(c->sets);
    free(c);
}

void decode_address(Cache *c, uint32_t address, uint32_t *offset, uint32_t *set_index, uint32_t *tag) {
    *offset = (address & c->offset_mask) >> 2;
    address >>= c->offset_bit_count;
    *set_index = address & c->set_index_mask;
    *tag = address >> c->set_index_bit_count;
}

uint32_t encode_address(Cache *c, uint32_t offset, uint32_t set_index, uint32_t tag) {
    return (tag << (c->offset_bit_count + c->set_index_bit_count)) |
           (set_index << c->offset_bit_count) |
           (offset << 2);
}

static int lookup_line(Cache *c, Cache_Set *set, uint32_t tag, Cache_Block **block_ptr) {
    Cache_Block *block;
    Cache_Block *invalid_block = NULL;
    for (size_t i = 0; i < c->way_count; i++) {
        block = set->ways + i;
        if (block->valid && block->tag == tag) break;
        if (!block->valid) invalid_block = block;
    }
    // If hit, return immediately
    if (block->valid && block->tag == tag) {
        *block_ptr = block;
        return TRUE;
    }

    // If there is invalid block, use it first
    if (invalid_block != NULL) {
        *block_ptr = invalid_block;
        return FALSE;
    }

    // If no match, block is the last way
    switch (c->policy) {
        case LRU:
            // The last way is least-recently-used for LRU
            *block_ptr = block;
            return FALSE;
        case RANDOM:
            *block_ptr = set->ways + (rand() % c->way_count);
            return FALSE;
    }
}

void move_block_to_front(Cache_Block *block, Cache_Block *head) {
    size_t len = block - head;
    if (len) {
        Cache_Block block_copy = *block;
        memmove(head + 1, head, sizeof(Cache_Block) * len);
        *head = block_copy;
    }
}

void update_block_recency(Cache *c, Cache_Block *block, Cache_Block *head) {
    switch (c->policy) {
        case LRU:
            move_block_to_front(block, head);
            break;
        case RANDOM:
            // Do nothing
            break;
    }
}

static void write_value_to_block(Cache_Block *block, uint32_t offset, uint32_t value) {
    if (value != block->data[offset]) {  // do not mark the block as dirty if the data is the same
        block->data[offset] = value;
        block->dirty = TRUE;
    }
}

int cache_test(Cache *c, uint32_t address) {
    uint32_t offset, set_index, tag;
    decode_address(c, address, &offset, &set_index, &tag);

    Cache_Set *set = c->sets + set_index;
    Cache_Block *block;
    int hit = lookup_line(c, set, tag, &block);  // get the hit block or the one to replace

    return hit ? 0 : CACHE_MISS_CYCLE;
}

static int cache_operate_32(Cache *c, uint32_t address, uint32_t *value_ptr, int write) {
    uint32_t offset, set_index, tag;
    decode_address(c, address, &offset, &set_index, &tag);

    Cache_Set *set = c->sets + set_index;
    Cache_Block *block;
    int hit = lookup_line(c, set, tag, &block);  // get the hit block or the one to replace

    int cycle_to_wait;

    if (hit) {

        if (!write) {
            *value_ptr = block->data[offset];
        } else {
            write_value_to_block(block, offset, *value_ptr);
        }
        cycle_to_wait = 0;

    } else {

        // Write back if dirty
        if (block->valid && block->dirty) {
            for (uint32_t i = 0; i < c->block_size_in_words; i++) {
                mem_write_32(encode_address(c, i, set_index, block->tag), block->data[i]);
            }
        }

        // Retrieve data from memory
        block->valid = TRUE;
        block->dirty = FALSE;
        block->tag = tag;
        for (uint32_t i = 0; i < c->block_size_in_words; i++) {
            block->data[i] = mem_read_32((address & (~c->offset_mask)) + (i << 2));
        }
        cycle_to_wait = CACHE_MISS_CYCLE;

        // Write data for a write operation
        if (write) {
            write_value_to_block(block, offset, *value_ptr);
        } else {
            *value_ptr = block->data[offset];
        }
    }

    update_block_recency(c, block, set->ways);

    return cycle_to_wait;
}

int cache_read_32(Cache *c, uint32_t address, uint32_t *value_ptr) {
    return cache_operate_32(c, address, value_ptr, FALSE);
}

int cache_write_32(Cache *c, uint32_t address, uint32_t value) {
    return cache_operate_32(c, address, &value, TRUE);
}

