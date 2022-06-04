void klee_unit_test_get_sign()
{
  int x = SYMBOLIC(int);
  int ret = get_sign(x);
  WATCH(ret);
}
