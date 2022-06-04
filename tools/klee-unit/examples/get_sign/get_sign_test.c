#ifndef AST_KLEE_UNIT_KLEE_UNIT_H
#define AST_KLEE_UNIT_KLEE_UNIT_H

extern void *__symbolic(unsigned long);
extern void __watch(void *);
extern void __let(int);

#define SYMBOLIC(type)               (*((type *) __symbolic(sizeof (type))))
#define SYMBOLIC_ARRAY(type, length) {*((type *) __symbolic(sizeof (type) * length))}

#define LET(cond)                    __let(cond)
#define WATCH(var)                   __watch((void *) (&(var)))

#endif

void klee_unit_test_get_sign()
{
  int x = SYMBOLIC(int);
  int ret = get_sign(x);
  WATCH(ret);
}


void klee_unit_test_get_sign()
{
  int x = SYMBOLIC(int);
  int ret = get_sign(x);
  WATCH(ret);
}

