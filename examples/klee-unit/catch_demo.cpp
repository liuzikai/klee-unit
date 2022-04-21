//
// Created by Zikai Liu on 4/16/22.
//

#define CATCH_CONFIG_MAIN  // This tells Catch to provide a main() - only do this in one cpp file
#include <catch.hpp>
#include <fakeit_free_func.hpp>
using namespace fakeit;

unsigned int Factorial(unsigned int number) {
    return number <= 1 ? number : Factorial(number - 1) * number;
}

TEST_CASE("Factorials are computed", "[factorial]") {
    REQUIRE(Factorial(1) == 1);
    REQUIRE(Factorial(2) == 2);
    REQUIRE(Factorial(3) == 6);
    REQUIRE(Factorial(10) == 3628800);
}

struct SomeInterface {
    virtual int foo(int) = 0;
};

TEST_CASE("FakeIt simple", "[fakeit]") {
    Mock<SomeInterface> mock;
    When(Method(mock,foo)).Return(2_Times(1));
    REQUIRE(mock.get().foo(42) == 1);
    Verify(Method(mock,foo).Using(42)).Exactly(Once);
}


extern "C"
{
void Function1(void);
}
float Function2(int);

//declare the mocks (must match the signature from component's API)
MockFree(void, Function1)
MockFree(float, Function2, int)

//use the mocks
TEST_CASE("FakeIt Free Function", "[fakeit]")
{
    //free function mock
    fakeit::When(FreeFunction(Function1)).Do([]() {std::cout << "Called Function1()" << std::endl; });
    fakeit::When(FreeFunction(Function2)).Return(10.0f);
    Function1();

    REQUIRE(Function2(5) == 10.0f);
    REQUIRE(Function2(5) == 10.0f);
}