#ifndef __KLEE_UNIT_HEADER_KLEE_DUMMY
#define __KLEE_UNIT_HEADER_KLEE_DUMMY

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define NO_OPT static __attribute__((noinline)) /* do not use static or functions are renamed despite extern "C" */

NO_OPT void klee_make_symbolic(void *array, size_t nbytes, const char *name) {}

NO_OPT void klee_silent_exit(int x) {}

NO_OPT uintptr_t klee_choose(uintptr_t n) { return n; }

NO_OPT unsigned klee_is_replay() { return 0; }

NO_OPT void klee_assume(uintptr_t x) {}

#define KLEE_GET_VALUE_STUB(suffix, type)                                      \
  NO_OPT type klee_get_value##suffix(type x) { return x; }

KLEE_GET_VALUE_STUB(f, float)
KLEE_GET_VALUE_STUB(d, double)
KLEE_GET_VALUE_STUB(l, long)
KLEE_GET_VALUE_STUB(ll, long long)
KLEE_GET_VALUE_STUB(_i32, int32_t)
KLEE_GET_VALUE_STUB(_i64, int64_t)

#undef KLEE_GET_VALUE_STUB

NO_OPT int klee_range(int begin, int end, const char *name) { return 0; }

NO_OPT void klee_prefer_cex(void *object, uintptr_t condition) {}

NO_OPT void klee_abort() {}

NO_OPT void klee_print_expr(const char *msg, ...) {}

NO_OPT void klee_set_forking(unsigned enable) {}

NO_OPT void klee_open_merge() {}

NO_OPT void klee_close_merge() {}

NO_OPT size_t klee_get_obj_size(void *ptr) { return 0; }

NO_OPT unsigned klee_is_symbolic(uintptr_t x) { return 0; }

NO_OPT void klee_watch_obj(void *ptr, const char *name) {}

#undef NO_OPT

#ifdef __cplusplus
}
#endif

#endif