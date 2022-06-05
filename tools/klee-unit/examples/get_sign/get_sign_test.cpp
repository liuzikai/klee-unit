
TEST_CASE("GET_SIGN_POSITIVE")
{
  int x = 0x1010101;
  int ret = get_sign(x);
  REQUIRE(ret == 0x1);
}

TEST_CASE("GET_SIGN_ZERO")
{
  int x = 0x0;
  int ret = get_sign(x);
  REQUIRE(ret == 0x0);
}

void klee_unit_test_get_sign()
{
  int x = SYMBOLIC(int);
  int ret = get_sign(x);
  WATCH(ret);
}

