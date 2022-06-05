//
// Created by liuzikai on 10/5/21.
//

#include "CppUTest/TestHarness_c.h"
#include "CppUTestExt/MockSupport_c.h"
#include "../src/cache.h"
#include "../src/cache_private.h"

static void check_cache_create(int way_count, int set_count, int block_size_in_bytes, uint32_t offset_mask,
                               uint32_t offset_bit_count, uint32_t set_index_mask, uint32_t set_index_bit_count) {
    Cache *c = cache_create(way_count, set_count, block_size_in_bytes, LRU);
    CHECK_C(c != NULL);
    CHECK_EQUAL_C_INT(c->way_count, way_count);
    CHECK_EQUAL_C_INT(c->set_count, set_count);
    CHECK_EQUAL_C_INT(c->block_size_in_words, block_size_in_bytes / 4);
    CHECK_EQUAL_C_UINT(c->offset_mask, offset_mask);
    CHECK_EQUAL_C_UINT(c->offset_bit_count, offset_bit_count);
    CHECK_EQUAL_C_UINT(c->set_index_mask, set_index_mask);
    CHECK_EQUAL_C_UINT(c->set_index_bit_count, set_index_bit_count);
    cache_destroy(c);
}

TEST_C(cache_test, create) {
    check_cache_create(4, 64, 32, 0x1F, 5, 0x3F, 6);
    check_cache_create(8, 256, 32, 0x1F, 5, 0xFF, 8);
    check_cache_create(1, 32, 4, 0x3, 2, 0x1F, 5);
}

TEST_C(cache_test, decode_encode_address) {
    uint32_t offset, set_index, tag;

    Cache *c = cache_create(4, 64, 32, LRU);

    decode_address(c, 0x12345678, &offset, &set_index, &tag);
    CHECK_EQUAL_C_UINT(0b110, offset);
    CHECK_EQUAL_C_UINT(0b110011, set_index);
    CHECK_EQUAL_C_UINT(0b100100011010001010, tag);
    CHECK_EQUAL_C_UINT(0x12345678, encode_address(c, offset, set_index, tag));

    decode_address(c, 0x3514ABCC, &offset, &set_index, &tag);
    CHECK_EQUAL_C_UINT(0b011, offset);
    CHECK_EQUAL_C_UINT(0b011110, set_index);
    CHECK_EQUAL_C_UINT(0b1101010001010010101, tag);
    CHECK_EQUAL_C_UINT(0x3514ABCC, encode_address(c, offset, set_index, tag));

    cache_destroy(c);

    c = cache_create(8, 256, 4, LRU);

    decode_address(c, 0x12345678, &offset, &set_index, &tag);
    CHECK_EQUAL_C_UINT(0, offset);
    CHECK_EQUAL_C_UINT(0b10011110, set_index);
    CHECK_EQUAL_C_UINT(0b1001000110100010101, tag);
    CHECK_EQUAL_C_UINT(0x12345678, encode_address(c, offset, set_index, tag));

    decode_address(c, 0x3514ABCC, &offset, &set_index, &tag);
    CHECK_EQUAL_C_UINT(0, offset);
    CHECK_EQUAL_C_UINT(0b11110011, set_index);
    CHECK_EQUAL_C_UINT(0b11010100010100101010, tag);
    CHECK_EQUAL_C_UINT(0x3514ABCC, encode_address(c, offset, set_index, tag));

    cache_destroy(c);
}

static void expect_mem_reads(const Cache *c, uint32_t address, const uint32_t *mem_val) {
    for (uint32_t i = 0; i < c->block_size_in_words; i++) {
        mock_c()->expectOneCall("mem_read_32")
                ->withUnsignedIntParameters("address", (address & ~c->offset_mask) + (i << 2))
                ->andReturnUnsignedIntValue(mem_val[i]);
    }
}

static void test_read_miss(Cache *c, uint32_t address, const uint32_t mem_val[], uint32_t expected_val) {
    expect_mem_reads(c, address, mem_val);

    uint32_t val;
    CHECK_EQUAL_C_INT(CACHE_MISS_CYCLE, cache_read_32(c, address, &val));
    CHECK_EQUAL_C_UINT(expected_val, val);

    mock_c()->checkExpectations();
    mock_c()->clear();
}

static void test_read_hit(Cache *c, uint32_t address, uint32_t expected_val) {
    uint32_t val;
    CHECK_EQUAL_C_INT(0, cache_read_32(c, address, &val));
    CHECK_EQUAL_C_UINT(expected_val, val);
}

const uint32_t read_words_1[] = {
        0x88888888, 0x77777777, 0x66666666, 0x55555555, 0x44444444, 0x33333333, 0x22222222, 0x11111111};
const uint32_t read_words_2[] = {
        0xFFFFFFFF, 0xEEEEEEEE, 0xDDDDDDDD, 0xCCCCCCCC, 0xBBBBBBBB, 0xAAAAAAAA, 0x99999999, 0x88888888};
const uint32_t read_words_3[] = {
        0xAAAAAAAA, 0xAAAAAAAA, 0xAAAAAAAA, 0xAAAAAAAA, 0xAAAAAAAA, 0xAAAAAAAA, 0xAAAAAAAA, 0xAAAAAAAA};
const uint32_t read_words_3_1[] = {
        0x31313131, 0x31313131, 0x31313131, 0x31313131, 0x31313131, 0x31313131, 0x31313131, 0x31313131};
const uint32_t read_words_3_2[] = {
        0x32323232, 0x32323232, 0x32323232, 0x32323232, 0x32323232, 0x32323232, 0x32323232, 0x32323232};
const uint32_t read_words_4[] = {
        0xFFFFEEEE, 0xFFFFEEEE, 0xFFFFEEEE, 0xFFFFEEEE, 0xFFFFEEEE, 0xFFFFEEEE, 0xFFFFEEEE, 0xFFFFEEEE};
const uint32_t read_words_5[] = {
        0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB};
const uint32_t read_words_6[] = {
        0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC};
const uint32_t read_words_7[] = {
        0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD};
const uint32_t read_words_8[] = {
        0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE};

TEST_C(cache_test, simple_read_miss) {
    Cache *c = cache_create(4, 64, 32, LRU);
    test_read_miss(c, 0, read_words_1, read_words_1[0]);
    test_read_miss(c, 0x20, read_words_1, read_words_1[0]);
    cache_destroy(c);
}

TEST_C(cache_test, simple_read_hit) {
    Cache *c = cache_create(4, 64, 32, LRU);
    test_read_miss(c, 0, read_words_1, read_words_1[0]);
    test_read_hit(c, 0, read_words_1[0]);
    test_read_hit(c, 0, read_words_1[0]);
    cache_destroy(c);
}

TEST_C(cache_test, read_same_block) {
    Cache *c = cache_create(4, 64, 32, LRU);
    test_read_miss(c, 0, read_words_1, read_words_1[0]);
    test_read_hit(c, 4, read_words_1[1]);
    test_read_hit(c, 0x10, read_words_1[4]);
    test_read_hit(c, 0x1C, read_words_1[7]);
    cache_destroy(c);
}

TEST_C(cache_test, move_block_to_front) {
    Cache_Block blocks[8];
    for (int i = 0; i < 8; i++) blocks[i].tag = i;

    move_block_to_front(blocks, blocks);
    for (int i = 0; i < 8; i++) CHECK_EQUAL_C_UINT(i, blocks[i].tag);

    move_block_to_front(blocks + 1, blocks);
    CHECK_EQUAL_C_UINT(1, blocks[0].tag);
    CHECK_EQUAL_C_UINT(0, blocks[1].tag);
    for (int i = 2; i < 8; i++) CHECK_EQUAL_C_UINT(i, blocks[i].tag);

    move_block_to_front(blocks + 1, blocks);
    for (int i = 0; i < 8; i++) CHECK_EQUAL_C_UINT(i, blocks[i].tag);

    move_block_to_front(blocks + 7, blocks);
    CHECK_EQUAL_C_UINT(7, blocks[0].tag);
    for (int i = 1; i < 8; i++) CHECK_EQUAL_C_UINT(i - 1, blocks[i].tag);

    move_block_to_front(blocks + 7, blocks);
    CHECK_EQUAL_C_UINT(6, blocks[0].tag);
    CHECK_EQUAL_C_UINT(7, blocks[1].tag);
    for (int i = 2; i < 8; i++) CHECK_EQUAL_C_UINT(i - 2, blocks[i].tag);

    move_block_to_front(blocks + 1, blocks);
    CHECK_EQUAL_C_UINT(7, blocks[0].tag);
    CHECK_EQUAL_C_UINT(6, blocks[1].tag);
    for (int i = 2; i < 8; i++) CHECK_EQUAL_C_UINT(i - 2, blocks[i].tag);
}

void read_test_with_different_ways(int way_count) {
    // Adapted from my old project: https://github.com/liuzikai/ECE411-RV32I-Processor
    Cache *c = cache_create(way_count, 8, 32, LRU);

    // TEST: read sequence 1
    test_read_miss(c, 0x00000000, read_words_1, 0x88888888);
    test_read_hit(c, 0x00000000, 0x88888888);
    test_read_hit(c, 0x00000008, 0x66666666);
    test_read_hit(c, 0x00000000, 0x88888888);
    test_read_hit(c, 0x0000001C, 0x11111111);

    // TEST: read seq 2, with the same index as seq 1
    test_read_miss(c, 0x1000000C, read_words_2, 0xCCCCCCCC);
    test_read_hit(c, 0x10000018, 0x99999999);

    // TEST: seq 1 should not be lost
    test_read_hit(c, 0x0000000C, 0x55555555);
    test_read_hit(c, 0x00000010, 0x44444444);

    // TEST: read seq 3, with a different index
    test_read_miss(c, 0x00000080, read_words_3, 0xAAAAAAAA);

    // TEST: seq 1 and 2 should not be lost
    test_read_hit(c, 0x10000000, 0xFFFFFFFF);
    test_read_hit(c, 0x00000008, 0x66666666);
    // Seq 2 is LRU

    if (way_count == 4) {
        // TEST: read seq 3.1 & 3.2, with the same index as seq 1 & 2
        test_read_miss(c, 0x2000000C, read_words_3_1, 0x31313131);
        test_read_miss(c, 0x3000000C, read_words_3_2, 0x32323232);
        // Seq 2 is LRU
    }

    // TEST: read seq 4, with the same index as seq 1 and 2. Seq 2 should be replaced
    test_read_miss(c, 0x80000000, read_words_4, 0xFFFFEEEE);

    // TEST: seq 1 should not miss
    test_read_hit(c, 0x00000000, 0x88888888);
    test_read_hit(c, 0x0000001C, 0x11111111);

    if (way_count == 4) {
        // TEST: seq 3.1 & 3.2 should not miss
        test_read_hit(c, 0x2000000C, 0x31313131);
        test_read_hit(c, 0x3000000C, 0x32323232);
    }

    // Seq 4 is LRU

    // TEST: seq 2 should miss, seq 4 should be replaced
    test_read_miss(c, 0x1000000C, read_words_2, 0xCCCCCCCC);

    // TEST: seq 4 should miss, seq 1 should be replaced
    test_read_miss(c, 0x80000000, read_words_4, 0xFFFFEEEE);

    // TEST: seq 3 should be totally unaffected
    test_read_hit(c, 0x00000084, 0xAAAAAAAA);

    // TEST: seq 1 should miss, seq 2 (2-way)/seq 3.1 (4-way) should be replaced
    test_read_miss(c, 0x00000000, read_words_1, 0x88888888);

    // TEST: seq 4 should not miss
    test_read_hit(c, 0x8000000C, 0xFFFFEEEE);

    if (way_count == 2) {

        // TEST: read seq 5, with the same index as seq 3
        test_read_miss(c, 0x03000080, read_words_5, 0xBBBBBBBB);

        // TEST: read seq 6, with the same index as seq 3 & 5. Seq 3 should be replaced (2-way)
        test_read_miss(c, 0x05000080, read_words_6, 0xCCCCCCCC);

        // TEST: read seq 7, with the same index as seq 6 & 5 (& 3 for 4-way). Seq 5 should be replaced (2-way)
        test_read_miss(c, 0x05500080, read_words_7, 0xDDDDDDDD);

        // TEST: seq 5 should miss. Seq 6 should be replaced
        test_read_miss(c, 0x03000080, read_words_5, 0xBBBBBBBB);

    } else if (way_count == 4) {

        // TEST: seq 3 should not miss
        test_read_hit(c, 0x00000084, 0xAAAAAAAA);

        // TEST: read seq 5, with the same index as seq 3
        test_read_miss(c, 0x03000080, read_words_5, 0xBBBBBBBB);

        // TEST: seq 5 should not miss.
        test_read_hit(c, 0x03000080, 0xBBBBBBBB);

        // TEST: read seq 6, with the same index as seq 3 & 5.
        test_read_miss(c, 0x05000080, read_words_6, 0xCCCCCCCC);

        // TEST: read seq 7, with the same index as seq 6 & 5 & 3.
        test_read_miss(c, 0x05500080, read_words_7, 0xDDDDDDDD);

        // TEST: read seq 8, with the same index as seq 3 & 5 & 6 & 7. Seq 3 should be replaced
        test_read_miss(c, 0x05600080, read_words_8, 0xEEEEEEEE);

        // TEST: read seq 3, seq 5 should be replaced
        test_read_miss(c, 0x00000080, read_words_3, 0xAAAAAAAA);

        // TEST: seq 6 should not miss
        test_read_hit(c, 0x05000080, 0xCCCCCCCC);

        // TEST: read seq 5, seq 7 should be replaced
        test_read_miss(c, 0x03000080, read_words_5, 0xBBBBBBBB);

    }

    cache_destroy(c);
}

TEST_C(cache_test, read_test_2_ways) {
    read_test_with_different_ways(2);
}

TEST_C(cache_test, read_test_4_ways) {
    read_test_with_different_ways(4);
}

static void test_write_miss(Cache *c, uint32_t address, const uint32_t mem_val[], uint32_t write_val) {
    expect_mem_reads(c, address, mem_val);
    CHECK_EQUAL_C_INT(CACHE_MISS_CYCLE, cache_write_32(c, address, write_val));
    mock_c()->checkExpectations();
    mock_c()->clear();
}

static void test_write_hit(Cache *c, uint32_t address, uint32_t write_val) {
    CHECK_EQUAL_C_INT(0, cache_write_32(c, address, write_val));
}

static void expect_mem_writes(const Cache *c, uint32_t address, const uint32_t *mem_val) {
    for (uint32_t i = 0; i < c->block_size_in_words; i++) {
        mock_c()->expectOneCall("mem_write_32")
                ->withUnsignedIntParameters("address", (address & ~c->offset_mask) + (i << 2))
                ->withUnsignedIntParameters("value", mem_val[i]);
    }
}

static void test_read_miss_with_wb(Cache *c, uint32_t address, const uint32_t mem_val[], uint32_t expected_val,
                                   uint32_t expected_wb_address, const uint32_t expected_wb_val[]) {
    expect_mem_writes(c, expected_wb_address, expected_wb_val);
    test_read_miss(c, address, mem_val, expected_val);
}

static void test_write_miss_with_wb(Cache *c, uint32_t address, const uint32_t mem_val[], uint32_t write_val,
                                    uint32_t expected_wb_address, const uint32_t expected_wb_val[]) {
    expect_mem_writes(c, expected_wb_address, expected_wb_val);
    test_write_miss(c, address, mem_val, write_val);
}

const uint32_t write_words_1[] = {
        0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD, 0xDDDDDDDD};

const uint32_t write_words_1_after[] = {
        0xEEEEEEEE, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC, 0xCCCCCCCC};

const uint32_t write_words_2[] = {
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000};

const uint32_t write_words_2_after[] = {
        0x11111111, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000};

const uint32_t write_words_3[] = {
        0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000};

const uint32_t write_words_3_after[] = {
        0x00000000, 0x00000000, 0x22002200, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000};

void write_test_with_different_ways(int way_count) {

    // Adapted from my old project: https://github.com/liuzikai/ECE411-RV32I-Processor

    Cache *c = cache_create(way_count, 8, 32, LRU);

    // Load data 1
    test_read_miss(c, 0xF0000000, write_words_1, 0xDDDDDDDD);

    // TEST: hit write to offset 0
    test_write_hit(c, 0xF0000000, 0xEEEEEEEE);

    // TEST: the data gets updated, while the other offset get unaffected
    test_read_hit(c, 0xF0000000, 0xEEEEEEEE);
    for (int i = 1; i < 8; i++) test_read_hit(c, 0xF0000000 + i * 4, 0xDDDDDDDD);

    // TEST: more writes to data 1
    for (int i = 1; i < 8; i++) test_write_hit(c, 0xF0000000 + i * 4, 0xCCCCCCCC);

    // TEST: write miss data 2
    test_write_miss(c, 0xE0000000, write_words_2, 0x11111111);
    test_read_hit(c, 0xE0000000, 0x11111111);
    for (int i = 1; i < 8; i++) test_read_hit(c, 0xE0000000 + i * 4, 0x00000000);

    // TEST: data 1 should not change
    test_read_hit(c, 0xF0000000, 0xEEEEEEEE);
    for (int i = 1; i < 8; i++) test_read_hit(c, 0xF0000000 + i * 4, 0xCCCCCCCC);

    if (way_count == 4) {
        // TEST: write miss data 2.1 & 2.2
        test_write_miss(c, 0xE1000000, write_words_2, 0x11111111);
        test_read_hit(c, 0xE1000000, 0x11111111);
        test_write_miss(c, 0xE2000000, write_words_2, 0x11111111);
        test_read_hit(c, 0xE2000000, 0x11111111);
    }

    // TEST: write miss data 3, replacing data 2
    test_write_miss_with_wb(c,
                            0xD0000008,
                            write_words_3,
                            0x22002200,
                            0xE0000000,
                            write_words_2_after
    );

    // TEST: data 1 should not change
    test_read_hit(c, 0xF0000000, 0xEEEEEEEE);
    for (int i = 1; i < 8; i++) test_read_hit(c, 0xF0000000 + i * 4, 0xCCCCCCCC);

    // TEST: data 3 should be updated
    test_read_hit(c, 0xD0000000, 0x00000000);
    test_read_hit(c, 0xD0000004, 0x00000000);
    test_read_hit(c, 0xD0000008, 0x22002200);
    test_read_hit(c, 0xD000000C, 0x00000000);
    test_read_hit(c, 0xD0000010, 0x00000000);

    if (way_count == 4) {
        // TEST: data 2.1 & 2.2 should not change
        test_read_hit(c, 0xE1000000, 0x11111111);
        test_read_hit(c, 0xE2000000, 0x11111111);
    }

    if (way_count == 2) {
        // TEST: write miss data 2, replacing data 1
        test_write_miss_with_wb(c,
                                0xE0000000,
                                write_words_2_after,
                                0x11111111,
                                0xF0000000,
                                write_words_1_after
        );

        // TEST: LRU but not dirty
        test_read_miss(c, 0xE00000C0, write_words_1, 0xDDDDDDDD);
        test_write_miss(c, 0xD00000C0, write_words_1, 0xBBBBBBBB);
        test_read_miss(c, 0xC00000C0, write_words_1, 0xDDDDDDDD);

    } else if (way_count == 4) {

        // TEST: write miss data 2, replacing data 1
        test_write_miss_with_wb(c,
                                0xE0000000,
                                write_words_2_after,
                                0x11111111,
                                0xF0000000,
                                write_words_1_after
        );
    }

    cache_destroy(c);
}

TEST_C(cache_test, write_test_2_ways) {
    write_test_with_different_ways(2);
}

TEST_C(cache_test, write_test_4_ways) {
    write_test_with_different_ways(4);
}