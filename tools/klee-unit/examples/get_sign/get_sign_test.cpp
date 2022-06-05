
TEST_CASE("POSITIVE")
{
  int x = 128;
  ASSERT(x >= 0);
  int ret = get_sign(x);
  REQUIRE(ret == 1);
}

TEST_CASE("ZERO")
{
  int x = 0;
  ASSERT(x >= 0);
  int ret = get_sign(x);
  REQUIRE(ret == 0);
}
