/* The dummy include replacing catch.hpp to make the whole program compile and runnable by KLEE */

/* Use the SAME guard macro as catch.hpp to replace it */
#ifndef TWOBLUECUBES_SINGLE_INCLUDE_CATCH_HPP_INCLUDED
#define TWOBLUECUBES_SINGLE_INCLUDE_CATCH_HPP_INCLUDED

#define INTERNAL_CATCH_UNIQUE_NAME_LINE2( name, line ) name##line
#define INTERNAL_CATCH_UNIQUE_NAME_LINE( name, line ) INTERNAL_CATCH_UNIQUE_NAME_LINE2( name, line )
#define INTERNAL_CATCH_UNIQUE_NAME( name ) INTERNAL_CATCH_UNIQUE_NAME_LINE( name, __LINE__ )

#define INTERNAL_CATCH_TESTCASE2( TestName, ... ) \
    static void TestName(); \
    static void TestName()
#define INTERNAL_CATCH_TESTCASE( ... ) \
    INTERNAL_CATCH_TESTCASE2( INTERNAL_CATCH_UNIQUE_NAME( C_A_T_C_H_T_E_S_T_ ), __VA_ARGS__ )

#define TEST_CASE( ... ) INTERNAL_CATCH_TESTCASE( __VA_ARGS__ )
#define TEST_CASE_METHOD( className, ... ) INTERNAL_CATCH_TESTCASE( __VA_ARGS__ )
#define METHOD_AS_TEST_CASE( method, ... ) INTERNAL_CATCH_TESTCASE( __VA_ARGS__ )
#define REGISTER_TEST_CASE( Function, ... ) INTERNAL_CATCH_TESTCASE( __VA_ARGS__ )
#define SECTION( ... )
#define DYNAMIC_SECTION( ... )
#define FAIL( ... )
#define FAIL_CHECK( ... )
#define SUCCEED( ... )
#define ANON_TEST_CASE()

#define REQUIRE( ... )

#endif
