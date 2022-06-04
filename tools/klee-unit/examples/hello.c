//
// Created by Zikai Liu on 4/15/22.
//

#include "klee_unit.h"
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

char foo2(int a, int b[], int c[10], int *d, struct some_struct s);
void test_foo2()
{
  int a = SYMBOLIC(int);
  int b[] = SYMBOLIC_ARRAY(int, UNKNOWN_LENGTH);
  int c[10] = SYMBOLIC_ARRAY(int, 10);
  int *d = UNKNOWN_POINTER;
  struct some_struct s = SYMBOLIC(struct some_struct);
  char ret = foo2(a, b, c, d, s);
}

int main() {
    int a = (int) 0;
    klee_make_symbolic(&a, sizeof(a), "a");
    CHECK_EQUAL_C_INT(a, 42);
    return get_sign(a);
}