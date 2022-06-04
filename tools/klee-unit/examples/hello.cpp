//
// Created by Zikai Liu on 4/15/22.
//

//
// Created by Zikai Liu on 4/15/22.
//

#define CATCH_CONFIG_MAIN
#include "klee/klee.h"
#include <catch.hpp>

void klee_make_symbolic(void *array, size_t nbytes, const char *name) {

}

int get_sign(int x) {
    if (x == 0)
        return 0;

    if (x < 0)
        return -1;
    else
        return 1;
}

TEST_CASE("Hello world") {
    int a;
    klee_make_symbolic(&a, sizeof(a), "a");
    REQUIRE(a == 42);
}