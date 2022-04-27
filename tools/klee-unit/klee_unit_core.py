# -*- encoding: utf-8 -*-
import os
import sys
import subprocess
from pycparser import c_parser, c_ast, c_generator, parse_file
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from ktest import KTest
import struct

class ArgumentDriverType(Enum):
    NONE = 0
    SYMBOLIC = 1
    SYMBOLIC_ARRAY = 2
    EXPANDED_ARRAY = 3
    EXPANDED_STRUCT = 4
    PTR_OUT = 5
    PTR_IN_OUT = 6


@dataclass
class ArgumentInfo:
    type_str: str
    name: str
    options: list[ArgumentDriverType]


class _ArgumentType(Enum):
    ID = 0
    FIXED_LENGTH_ARRAY = 1
    VARIABLE_LENGTH_ARRAY = 2
    STRUCT = 3
    PTR = 4


@dataclass
class _ArgumentInfo:
    param: c_ast.Decl
    type: _ArgumentType
    option: ArgumentDriverType = ArgumentDriverType.NONE


class DriverGenerator:
    NONE_PLACEHOLDER = "?"

    def __init__(self, src_file: str, test_file: str) -> None:
        super().__init__()
        self._src_file = src_file
        self._test_file = test_file

        self._parser = c_parser.CParser()
        self._generator = c_generator.CGenerator()

        self._src_ast: Optional[c_ast.FileAST] = None
        self._func_decls: Optional[dict[str, c_ast.FuncDecl]] = None
        self._current_func_name: Optional[str] = None
        self._args: Optional[dict[str, _ArgumentInfo]] = None
        self._watch_ret = False
        self._driver_name: Optional[str] = None
        self._driver_ast: Optional[c_ast.FileAST] = None
        self._watch_vars: Optional[list[str]] = None
        self._test_cases: Optional[list[dict[str, bytes]]] = None

        self.reload_src()

    def reload_src(self) -> None:
        # FIXME: -xc++ is required for Apple clang but may not work for other compilers
        self._src_ast = parse_file(self._src_file, use_cpp=True, cpp_args='-xc++', parser=self._parser)

    def analyze_src(self) -> dict[str, str]:
        """
        Analyze the source file.
        :return: dict of {function name: function signature}
        """
        if self._src_ast is None:
            raise RuntimeError("reload_src is required before analyze_src")

        class _FuncDefVisitor(c_ast.NodeVisitor):

            def __init__(self, names: dict[str, str], decls: dict[str, c_ast.FuncDecl],
                         generator: c_generator.CGenerator) -> None:
                super().__init__()
                self.names = names
                self.decls = decls
                self.generator = generator

            def visit_FuncDecl(self, node: c_ast.FuncDecl):
                self.names[node.type.declname] = self.generator.visit_FuncDecl(node)
                self.decls[node.type.declname] = node

        ret = {}
        self._func_decls = {}
        v = _FuncDefVisitor(ret, self._func_decls, self._generator)
        v.visit(self._src_ast)
        return ret

    def analyze_func(self, name: str) -> (list[ArgumentInfo], bool):
        """
        Analyze the function and return a list of ArgumentInfo.
        :param name: function name
        :return: (list of ArgumentInfo, whether the function has return value (watch return by default if True))
        """
        if self._func_decls is None:
            raise RuntimeError("analyze_src is required before analyze_func")

        self._current_func_name = name
        uut_decl = self._func_decls[name]

        # Process return value
        ret_type_id = uut_decl.type.type.names[0]
        if ret_type_id == "void":
            self._watch_ret = False
        else:
            self._watch_ret = True

        # Process arguments
        self._args = {}

        if uut_decl.args is None:
            return [], self._watch_ret

        ret = []
        for param in uut_decl.args.params:

            # Decide available generators for each type of arguments
            if type(param.type) is c_ast.TypeDecl:
                options = [ArgumentDriverType.SYMBOLIC]
                if type(param.type.type) is c_ast.IdentifierType:
                    arg_type = _ArgumentType.ID
                elif type(param.type.type) is c_ast.Struct:
                    arg_type = _ArgumentType.STRUCT
                    options.append(ArgumentDriverType.EXPANDED_STRUCT)
                else:
                    raise RuntimeError("Unsupported argument subtype: {}".format(param.type.type))
            elif type(param.type) is c_ast.ArrayDecl:
                options = [ArgumentDriverType.SYMBOLIC_ARRAY]
                if param.type.dim is not None and type(param.type.dim) is c_ast.Constant:
                    arg_type = _ArgumentType.FIXED_LENGTH_ARRAY
                    options.append(ArgumentDriverType.EXPANDED_ARRAY)
                else:
                    arg_type = _ArgumentType.VARIABLE_LENGTH_ARRAY
            elif type(param.type) is c_ast.PtrDecl:
                arg_type = _ArgumentType.PTR
                options = [ArgumentDriverType.SYMBOLIC_ARRAY, ArgumentDriverType.PTR_OUT,
                           ArgumentDriverType.PTR_IN_OUT]
            else:
                raise RuntimeError("Unsupported argument type: {}".format(param.type))

            options.append(ArgumentDriverType.NONE)  # put None at last
            arg = ArgumentInfo(type_str=self._generator.visit(param.type), name=param.name, options=options)

            ret.append(arg)
            self._args[param.name] = _ArgumentInfo(param=param, type=arg_type)

        return ret, self._watch_ret

    def set_arg_option(self, name: str, option: ArgumentDriverType) -> None:
        if self._args is None:
            raise RuntimeError("analyze_func is required before set_arg_option")

        self._args[name].option = option

    def set_watch_ret(self, watch: bool) -> None:
        self._watch_ret = watch

    @staticmethod
    def _create_type_decl_by_identifier(name: str, type_id: str) -> c_ast.TypeDecl:
        return c_ast.TypeDecl(
            declname=name,
            quals=[], align=[],
            type=c_ast.IdentifierType(
                names=[type_id]
            )
        )

    @staticmethod
    def _create_var_decl(param: c_ast.Decl, name: str, type: c_ast.Node, init_val: c_ast.Node) -> c_ast.Decl:
        return c_ast.Decl(
            name=name,
            quals=param.quals, align=param.align, storage=param.storage, funcspec=param.funcspec,
            type=type,
            init=init_val,
            bitsize=param.bitsize)

    @staticmethod
    def _create_func_call(name: str, arg_list: list[c_ast.Node]) -> c_ast.FuncCall:
        return c_ast.FuncCall(
            name=c_ast.ID(name),
            args=c_ast.ExprList(arg_list)
        )

    def generate_test_driver(self) -> str:
        if self._current_func_name is None or self._args is None:
            raise RuntimeError("analyze_func is required before generate_test_driver")

        driver_body_item = []
        arg_ids = []

        # Generate argument drivers
        for arg_name, info in self._args.items():
            param = info.param

            if info.option == ArgumentDriverType.NONE:
                var_decl = self._create_var_decl(param, arg_name, param.type, c_ast.ID(self.NONE_PLACEHOLDER))
                driver_body_item.append(var_decl)
            elif info.option == ArgumentDriverType.SYMBOLIC:
                var_decl = self._create_var_decl(param, arg_name, param.type,
                                                 # trick to generate type substitution
                                                 self._create_func_call("SYMBOLIC", [param.type]))
                driver_body_item.append(var_decl)
            elif info.option == ArgumentDriverType.SYMBOLIC_ARRAY:
                if info.type == _ArgumentType.FIXED_LENGTH_ARRAY:
                    dim = param.type.dim
                else:
                    dim = c_ast.ID(self.NONE_PLACEHOLDER)

                if info.type == _ArgumentType.PTR:
                    var_type = c_ast.ArrayDecl(type=param.type.type, dim=None, dim_quals=None)
                else:
                    var_type = param.type

                var_decl = self._create_var_decl(param, arg_name, var_type,
                                                 # notice the double .type to extract inner type
                                                 self._create_func_call("SYMBOLIC_ARRAY", [param.type.type, dim]))
                driver_body_item.append(var_decl)

            elif info.option == ArgumentDriverType.EXPANDED_ARRAY:
                assert param.type.dim is not None and type(param.type.dim) is c_ast.Constant
                count = int(param.type.dim.value)
                var_decl = self._create_var_decl(param, arg_name, param.type,
                                                 c_ast.InitList([
                                                     # notice the double .type to extract inner type
                                                     self._create_func_call("SYMBOLIC", [param.type.type]) for _ in
                                                     range(count)
                                                 ]))
                driver_body_item.append(var_decl)

            elif info.option == ArgumentDriverType.EXPANDED_STRUCT:
                raise NotImplementedError("EXPANDED_STRUCT is not supported yet")
            elif info.option == ArgumentDriverType.PTR_OUT:
                raise NotImplementedError("PTR_OUT is not supported yet")
            elif info.option == ArgumentDriverType.PTR_IN_OUT:
                raise NotImplementedError("PTR_IN_OUT is not supported yet")
            else:
                raise RuntimeError("Unknown argument driver type: {}".format(info.option))

            arg_ids.append(c_ast.ID(arg_name))

        # Generate return value driver
        ret_type_id = self._func_decls[self._current_func_name].type.type.names[0]
        call_decl = self._create_func_call(self._current_func_name, arg_ids)
        if not self._watch_ret:
            driver_body_item.append(call_decl)
        else:
            ret_decl = c_ast.Decl(
                name="ret",
                quals=[], align=[], storage=[], funcspec=[],
                type=self._create_type_decl_by_identifier("ret", ret_type_id),
                init=call_decl,
                bitsize=None
            )
            driver_body_item.append(ret_decl)
            driver_body_item.append(self._create_func_call("WATCH", [c_ast.ID("ret")]))

        # Generate test driver function
        driver_name = f"klee_unit_test_{self._current_func_name}"
        driver_body = c_ast.Compound(block_items=driver_body_item)
        driver_decl = c_ast.FuncDef(
            decl=c_ast.Decl(
                name=driver_name,
                quals=[], align=[], storage=[], funcspec=[],
                type=c_ast.FuncDecl(
                    args=None,
                    type=self._create_type_decl_by_identifier(driver_name, "void"),
                ),
                init=None, bitsize=None
            ),
            param_decls=None,
            body=driver_body
        )

        driver_src = self._generator.visit(c_ast.FileAST(
            [driver_decl]
        ))

        if not os.path.exists(self._test_file):
            with open(self._test_file, "w", encoding="utf-8") as f:
                f.write('#include "klee_unit.h"\n\n')
                f.write(driver_src)
        else:
            with open(self._test_file, "a", encoding="utf-8") as f:
                f.write("\n")
                f.write(driver_src)

        self._driver_name = driver_name
        return driver_src

    def _lookup_test_driver_func(self, ast: c_ast.FileAST) -> Optional[tuple[c_ast.FuncDef, int, int]]:
        """
        Lookup test driver function in the AST.
        :param ast: AST to be searched
        :return: (func_def, start_line, end_line (exclusive))
        """
        for i, e in enumerate(ast.ext):
            if type(e) is c_ast.FuncDef:
                if e.decl and e.decl.name == self._driver_name:
                    start_line = int(e.coord.line) - 1  # coord.line is 1-based
                    end_line = int(ast.ext[i + 1].coord.line) - 1 if i + 1 < len(ast.ext) else None
                    return e, start_line, end_line
        return None

    def _try_rewrite_statement(self, e) -> list[c_ast.Node]:
        if type(e) is c_ast.Decl and \
                type(e.init) is c_ast.UnaryOp and e.init.op == "*" and \
                type(e.init.expr) is c_ast.Cast and \
                type((func_call := e.init.expr.expr)) is c_ast.FuncCall and \
                type(func_call.name) is c_ast.ID and func_call.name.name == "__symbolic":

            var_name = e.name

            # Rewrite the function call
            func_call.name.name = "klee_make_symbolic"
            func_call.args.exprs.insert(0, c_ast.UnaryOp(op="&", expr=c_ast.ID(var_name)))
            func_call.args.exprs.append(c_ast.Constant(type="string", value=f'"{var_name}"'))

            # Clear the initializer
            e.init = None

            ret = [e, func_call]

            self._watch_vars.append(var_name)
        elif type(e) is c_ast.FuncCall and type(e.name) is c_ast.ID and e.name.name == "__watch":
            assert len(e.args.exprs) == 1 and type(e.args.exprs[0]) is c_ast.Cast
            cast = e.args.exprs[0]
            assert type(cast.expr) is c_ast.UnaryOp and cast.expr.op == "&" and type(cast.expr.expr) is c_ast.ID
            var_name = cast.expr.expr.name

            # Rewrite the function call
            e.name.name = "klee_make_symbolic"
            e.args.exprs = [c_ast.UnaryOp(op="&", expr=c_ast.ID(var_name)),
                            c_ast.UnaryOp(op="sizeof", expr=c_ast.ID(var_name)),
                            c_ast.Constant(type="string", value=f'"{var_name}"')]
            ret = [e]

            self._watch_vars.append(var_name)
        else:
            ret = [e]

        return ret

    def generate_klee_driver(self) -> list[str]:
        """
        Generate KLEE driver function.
        :return: list of watched variables
        """
        if self._driver_name is None:
            raise RuntimeError("generate_test_driver is required before generate_klee_driver")

        self._watch_vars = []

        # FIXME: -xc++ is required for Apple clang but may not work for other compilers
        self._driver_ast = parse_file(self._test_file, use_cpp=True, cpp_args='-xc++', parser=self._parser)  # substitute the macros
        driver_func, start_line, end_line = self._lookup_test_driver_func(self._driver_ast)
        if driver_func is None:
            raise RuntimeError("Cannot find test driver function")

        # Rewrite the test driver function as main()
        print(driver_func.coord)
        driver_func.decl.name = "main"
        driver_func.decl.type.type.declname = "main"
        driver_func.decl.type.type.type.names = ["int"]
        new_body = []
        for e in driver_func.body.block_items:
            new_body.extend(self._try_rewrite_statement(e))  # change self._watch_vars inside
        driver_func.body.block_items = new_body

        # driver_func.show()

        # Generate KLEE test driver source code
        klee_driver_src = self._generator.visit(driver_func)
        # print(klee_driver_src)

        # Read the original source code
        with open(self._test_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Replace the test driver function with KLEE test driver function
        with open(self._test_file, "w", encoding="utf-8") as f:
            if start_line > 0:
                f.writelines(lines[:start_line])
            f.write(f'#include <klee/klee.h>\n')
            f.write(f'#include "{self._src_file}"\n\n')
            f.write(klee_driver_src)
            f.write('void *__symbolic(unsigned long s) { (void) s; return 0; }\n')
            f.write('void __watch(void *ptr) { (void) ptr; }\n')
            f.write('void __let(int cond) { (void) cond; }\n')
            # FIXME: if there is nothing in the AST after the driver, everything will be overwritten
            if end_line is not None:
                f.writelines(lines[end_line:])

        return self._watch_vars

    def run_klee(self, add_test_case_callback: Callable[[int, list[str]], None]) -> None:

        # Generate LLVM bitcode
        bc_filename = os.path.splitext(self._test_file)[0] + ".bc"
        try:
            # Use of universal_newlines to treat all newlines as \n for Python's purpose
            output = subprocess.check_output(
                # FIXME: include path
                ["clang", "-I", "/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/include",
                 "-emit-llvm", "-c", "-g", "-O0", self._test_file,
                 "-o", bc_filename], universal_newlines=True)
        except OSError as e:
            raise RuntimeError("Unable to generate LLVM bitcode. Error: %s" % e)

        # print(output)

        output_dir = f"klee-out-{self._current_func_name}"
        if os.path.exists(output_dir):
            os.system(f"rm -rf {output_dir}")

        # Run KLEE
        try:
            # Use of universal_newlines to treat all newlines as \n for Python's purpose
            output = subprocess.check_output(
                # FIXME: include PATH
                ["/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/cmake-build-release/bin/klee",
                 f"-output-dir={output_dir}", bc_filename], universal_newlines=True)
        except OSError as e:
            raise RuntimeError("Unable to run KLEE. Error: %s" % e)

        print(output)

        # Extract the generated test cases
        self._test_cases = []
        index = 1
        while os.path.exists(filename := f"{output_dir}/test{str(index).zfill(6)}.ktest"):

            # Extract bytes of watched variables
            test_case = {}
            ktest = KTest.fromfile(filename)
            for name, data in ktest.objects:
                if name in self._watch_vars:
                    test_case[name] = data
            self._test_cases.append(test_case)

            # Format the variables
            formated_vars = []
            for name in self._watch_vars:
                if name in test_case:
                    data = test_case[name]
                    for n, m in [(1, 'b'), (2, 'h'), (4, 'i'), (8, 'q')]:
                        if len(data) == n:
                            formated_vars.append(f"{struct.unpack(m, data)[0]}")
                            break

                else:
                    RuntimeError(f"{name} is not found in {filename}")
            add_test_case_callback(index - 1, formated_vars)

            index += 1


if __name__ == '__main__':
    session = DriverGenerator(
        src_file="/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/examples/klee-unit/get_sign.c",
        test_file="/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/examples/klee-unit/get_sign_test.c")
    funcs = session.analyze_src()
    print("Functions:", ", ".join(funcs.keys()))

    session.analyze_func("get_sign")

    print("Generate test driver...")
    session.set_arg_option("x", ArgumentDriverType.SYMBOLIC)
    session.generate_test_driver()

    print("Press any key to continue...")
    input()

    print(session.generate_klee_driver())

    def add_test_case(index, values):
        print(f"Test case {index}: {', '.join(values)}")

    session.run_klee(add_test_case)

