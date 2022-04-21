//
// Created by liuzikai on 10/5/21.
//

#include "../src/shell.h"
#include "CppUTest/TestHarness_c.h"
#include "CppUTestExt/MockSupport_c.h"

uint32_t stat_cycles, stat_inst_retire, stat_inst_fetch, stat_squash;

uint32_t mem_read_32(uint32_t address) {
    mock_c()->actualCall("mem_read_32")
            ->withUnsignedIntParameters("address", address);
    return mock_c()->returnValue().value.unsignedIntValue;
}

void mem_write_32(uint32_t address, uint32_t value) {
    mock_c()->actualCall("mem_write_32")
            ->withUnsignedIntParameters("address", address)
            ->withUnsignedIntParameters("value", value);
}