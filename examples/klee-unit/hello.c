//
// Created by Zikai Liu on 4/15/22.
//

#include <cester.h>
//#include <klee/klee.h>

//void klee_make_symbolic(void *array, size_t nbytes, const char *name) {
//
//}

//int get_sign(int x) {
//    if (x == 0)
//        return 0;
//
//    if (x < 0)
//        return -1;
//    else
//        return 1;
//}

CESTER_TEST(test_one, inst,
        cester_assert_equal(NULL, ((void*)0));
)

//int main() {
//    int a;
//    klee_make_symbolic(&a, sizeof(a), "a");
//    CHECK_EQUAL_C_INT(a, 42);
//    return get_sign(a);
//}