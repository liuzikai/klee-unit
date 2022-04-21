// https://github.com/eranpeer/FakeIt/issues/163

#pragma once
#include "fakeit.hpp"

#ifdef _MSC_VER // Microsoft compilers

#define GET_ARG_COUNT(...)  INTERNAL_EXPAND_ARGS_PRIVATE(INTERNAL_ARGS_AUGMENTER(__VA_ARGS__))

#define INTERNAL_ARGS_AUGMENTER(...) unused, __VA_ARGS__
#define INTERNAL_EXPAND(x) x
#define INTERNAL_EXPAND_ARGS_PRIVATE(...) INTERNAL_EXPAND(INTERNAL_GET_ARG_COUNT_PRIVATE(__VA_ARGS__, 69, 68, 67, 66, 65, 64, 63, 62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0))
#define INTERNAL_GET_ARG_COUNT_PRIVATE(_1_, _2_, _3_, _4_, _5_, _6_, _7_, _8_, _9_, _10_, _11_, _12_, _13_, _14_, _15_, _16_, _17_, _18_, _19_, _20_, _21_, _22_, _23_, _24_, _25_, _26_, _27_, _28_, _29_, _30_, _31_, _32_, _33_, _34_, _35_, _36, _37, _38, _39, _40, _41, _42, _43, _44, _45, _46, _47, _48, _49, _50, _51, _52, _53, _54, _55, _56, _57, _58, _59, _60, _61, _62, _63, _64, _65, _66, _67, _68, _69, _70, count, ...) count

#else // Non-Microsoft compilers

#define GET_ARG_COUNT(...) INTERNAL_GET_ARG_COUNT_PRIVATE(0, ## __VA_ARGS__, 70, 69, 68, 67, 66, 65, 64, 63, 62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
#define INTERNAL_GET_ARG_COUNT_PRIVATE(_0, _1_, _2_, _3_, _4_, _5_, _6_, _7_, _8_, _9_, _10_, _11_, _12_, _13_, _14_, _15_, _16_, _17_, _18_, _19_, _20_, _21_, _22_, _23_, _24_, _25_, _26_, _27_, _28_, _29_, _30_, _31_, _32_, _33_, _34_, _35_, _36, _37, _38, _39, _40, _41, _42, _43, _44, _45, _46, _47, _48, _49, _50, _51, _52, _53, _54, _55, _56, _57, _58, _59, _60, _61, _62, _63, _64, _65, _66, _67, _68, _69, _70, count, ...) count

#endif

#define MAKE_PARAMS_0()
#define MAKE_PARAMS_1(type) type arg1
#define MAKE_PARAMS_2(type1, type2) type1 arg1, type2 arg2
#define MAKE_PARAMS_3(type1, type2, type3) type1 arg1, type2 arg2, type3 arg3
//.. add as many MAKE_PARAMS_* as you need

#define MAKE_PARAMS_N(N, ...) MAKE_PARAMS_##N(__VA_ARGS__)
#define MAKE_PARAMS_FORCE_N(N, ...) MAKE_PARAMS_N(N, __VA_ARGS__)
#define MAKE_PARAMS(...) MAKE_PARAMS_FORCE_N(GET_ARG_COUNT(__VA_ARGS__), __VA_ARGS__)


#define MAKE_ARGS_0()
#define MAKE_ARGS_1(type) arg1
#define MAKE_ARGS_2(t1, t2) arg1, arg2
#define MAKE_ARGS_3(t1, t2, t3) arg1, arg2, arg3
//.. add as many MAKE_ARGS_* as you have MAKE_PARAMS_*

#define MAKE_ARGS_N(N, ...) MAKE_ARGS_##N(__VA_ARGS__)
#define MAKE_ARGS_FORCE_N(N, ...) MAKE_ARGS_N(N, __VA_ARGS__)
#define MAKE_ARGS(...) MAKE_ARGS_FORCE_N(GET_ARG_COUNT(__VA_ARGS__), __VA_ARGS__)

namespace fakeit
{

//free function mock helper for fakeit
#define FreeFunction(Function) Method(Function ## _mock, Function)
#define MockFree(ReturnType, Function, ...) \
struct Function ## _interface \
{ \
   virtual ReturnType Function(MAKE_PARAMS(__VA_ARGS__)) = 0; \
}; \
static fakeit::Mock<Function ## _interface> Function ## _mock; \
ReturnType Function(MAKE_PARAMS(__VA_ARGS__)) \
{ \
    return Function ## _mock.get().Function(MAKE_ARGS(__VA_ARGS__)); \
};
}