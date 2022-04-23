//
// Created by Zikai Liu on 4/21/22.
//

#ifndef AST_KLEE_UNIT_KLEE_UNIT_H
#define AST_KLEE_UNIT_KLEE_UNIT_H

extern void *__symbolic;

#define SYMBOLIC(type)               (*((type *) __symbolic))
#define SYMBOLIC_ARRAY(type, length) {(type) (length)}

#define LET(cond)                    do { if (cond); } while(0)
#define WATCH(var)                   do { __symbolic = (void *)(&(var)); } while(0)

#endif // AST_KLEE_UNIT_KLEE_UNIT_H
