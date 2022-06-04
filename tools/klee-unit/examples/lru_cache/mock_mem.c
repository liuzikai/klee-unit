//
// Created by liuzikai on 10/5/21.
//

#include "mock_mem.h"

int expected_read_count = 0;
uint32_t expected_read_ret[RECORD_COUNT];

int actual_read_count = 0;
uint32_t actual_read_addr[RECORD_COUNT];

uint32_t mem_read_32(uint32_t addr) {
  uint32_t ret;
  if (actual_read_count < RECORD_COUNT) {
    actual_read_addr[actual_read_count] = addr;
    ret = expected_read_ret[actual_read_count];
  } else {
    ret = 0xDEADBEEF;
  }
  actual_read_count++;
  return ret;
}

int expected_write_count = 0;
int actual_write_count = 0;
uint32_t actual_write_addr[RECORD_COUNT];
uint32_t actual_write_value[RECORD_COUNT];

void mem_write_32(uint32_t addr, uint32_t value) {
  if (actual_write_count < RECORD_COUNT) {
    actual_write_addr[actual_write_count] = addr;
    actual_write_value[actual_write_count] = value;
  }
  actual_write_count++;
}