//
// Created by Zikai Liu on 5/23/22.
//

#ifndef MOCK_MEM_H
#define MOCK_MEM_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

#define RECORD_COUNT 64

extern int expected_read_count;
extern uint32_t expected_read_ret[RECORD_COUNT];

extern int actual_read_count;
extern uint32_t actual_read_addr[RECORD_COUNT];

extern int expected_write_count;
extern int actual_write_count;
extern uint32_t actual_write_addr[RECORD_COUNT];
extern uint32_t actual_write_value[RECORD_COUNT];

#ifdef __cplusplus
}
#endif

#endif
