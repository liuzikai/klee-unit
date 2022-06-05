# -*- encoding: utf-8 -*-
import os
import sys
import subprocess
from pycparser import c_parser, c_ast, c_generator, parse_file
from typing import Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import tempfile
import copy

from ktest import KTest, KTestError
import struct

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
KLEE_INCLUDE = os.path.join(CURRENT_DIR, "../../include")
KLEE_UNIT_INCLUDE = os.path.join(CURRENT_DIR, "include")
FAKE_LIBC_INCLUDE = os.path.join(CURRENT_DIR, "include/fake_libc_include")

KLEE_HEADER_FILENAME = os.path.join(KLEE_INCLUDE, "klee/klee.h")
KLEE_UNIT_HEADER_FILENAME = os.path.join(KLEE_UNIT_INCLUDE, "klee_unit.h")
KLEE_DUMMY_FILENAME = os.path.join(KLEE_UNIT_INCLUDE, "klee_dummy.h")
CATCH_DUMMY_FILENAME = os.path.join(KLEE_UNIT_INCLUDE, "catch_dummy.hpp")


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


class VarNotFoundError(Exception):
    pass


class KLEEUnitSession:
    NONE_PLACEHOLDER = "?"

    def __init__(self) -> None:
        super().__init__()

        # Check executables
        print(f'Found klee... {self._get_version("klee")}')
        print(f'Found clang... {self._get_version("clang")}')
        print(f'Found llvm-dis... {self._get_version("llvm-dis")}')

        self._cmake_mode = False
        self._src_file: Optional[str] = None
        self._project_dir: Optional[str] = None
        self._target: Optional[str] = None
        self._test_file: Optional[str] = None
        self._cmake_build_dir: Optional[str] = None
        self._tmp_test_file: Optional[str] = None
        self._klee_driver_file: Optional[str] = None

        self._parser = c_parser.CParser()
        self._generator = c_generator.CGenerator()

        self._src_ast: Optional[c_ast.FileAST] = None
        self._func_decls: Optional[dict[str, c_ast.FuncDecl]] = None
        self._current_func_name: Optional[str] = None
        self._args: Optional[dict[str, _ArgumentInfo]] = None
        self._watch_ret = False
        self._driver_name: Optional[str] = None
        self._driver_ast: Optional[c_ast.FileAST] = None
        self._heading_lines = None
        self._watch_vars: Optional[list[str]] = None
        self._test_cases: Optional[list[dict[str, bytes]]] = None

        # Create a temporary directory for KLEE
        self._tmp_dir = tempfile.TemporaryDirectory()
        print("Temporary directory:", self._tmp_dir.name)

        self._bc_filename: Optional[str] = None
        self._klee_output_dir: Optional[str] = None
        self._klee_proc = None

        self._driver_func_ast_copy: Optional[c_ast.FileAST] = None

    def set_src_file(self, src_file: str) -> None:
        self._src_file = os.path.abspath(src_file)

    def set_test_file(self, test_file: str) -> None:
        self._test_file = os.path.abspath(test_file)

    def set_single_file_mode(self) -> None:
        self._cmake_mode = False

    def set_cmake_mode(self, project_dir: str, target: str) -> None:
        self._cmake_mode = True
        self._project_dir = os.path.abspath(project_dir)
        self._target = target

    @staticmethod
    def _get_version(executable: str) -> str:
        try:
            version = subprocess.run([executable, "--version"], capture_output=True).stdout.decode("utf-8")
        except FileNotFoundError as e:
            raise RuntimeError(f"{executable} is not found in the system") from e
        return version.splitlines(keepends=False)[0]

    def run_cmake(self) -> (int, str):
        if self._project_dir is None:
            raise RuntimeError("Project directory is not set")

        self._cmake_build_dir = os.path.join(self._tmp_dir.name, "build_klee_unit")
        if not os.path.exists(self._cmake_build_dir):
            os.makedirs(self._cmake_build_dir, exist_ok=True)

        cmds = ["cmake",
                f"-DCMAKE_C_FLAGS='-include \"{CATCH_DUMMY_FILENAME}\" -include \"{KLEE_DUMMY_FILENAME}\" -include \"{KLEE_UNIT_HEADER_FILENAME}\" -include \"{KLEE_HEADER_FILENAME}\"'",
                f"-DCMAKE_CXX_FLAGS='-include \"{CATCH_DUMMY_FILENAME}\" -include \"{KLEE_DUMMY_FILENAME}\" -include \"{KLEE_UNIT_HEADER_FILENAME}\" -include \"{KLEE_HEADER_FILENAME}\"'",
                self._project_dir]
        proc = subprocess.run(
            cmds,
            cwd=self._cmake_build_dir,
            env=dict(os.environ, **{
                "CC": "wllvm",
                "CXX": "wllvm++",
                "WLLVM_CONFIGURE_ONLY": "1",
                "LLVM_COMPILER": "clang",
            }),
            capture_output=True,
            universal_newlines=True)

        return proc.returncode, "+ " + " ".join(cmds) + "\n" + proc.stdout

    def analyze_src(self) -> dict[str, str]:
        """
        Analyze the source file.
        :return: dict of {function name: function signature}
        """

        # Check if the source file is set
        if self._src_file is None:
            raise RuntimeError("Source file is not set")

        # Check if the source file exists
        if not os.path.exists(self._src_file):
            raise RuntimeError(f"Source file {self._src_file} does not exist")

        self._src_ast = parse_file(self._src_file, use_cpp=True, cpp_args=[
            '-xc++',
            f'-I{FAKE_LIBC_INCLUDE}',
        ], parser=self._parser)

        self._src_ast.show()

        class _FuncDefVisitor(c_ast.NodeVisitor):

            def __init__(self, names: dict[str, str], decls: dict[str, c_ast.FuncDecl],
                         generator: c_generator.CGenerator) -> None:
                super().__init__()
                self.names = names
                self.decls = decls
                self.generator = generator

            def visit_Decl(self, node: c_ast.Decl):
                if isinstance(node.type, c_ast.FuncDecl):
                    func_name = node.name
                    self.names[func_name] = self.generator.visit_FuncDecl(node.type)
                    self.decls[func_name] = node.type

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
            raise RuntimeError("The function is not analyzed yet")

        self._args[name].option = option

    def set_watch_ret(self, watch: bool) -> None:
        if self._args is None:
            raise RuntimeError("The function is not analyzed yet")

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
        # Check if the test file is set
        if self._test_file is None:
            raise RuntimeError("Test file is not set")

        if self._current_func_name is None or self._args is None:
            raise RuntimeError("Analyze the function before generating test driver")

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
                f.write('#include "catch.hpp"\n\n')
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

    def _rewrite_statement_to_klee(self, e) -> list[c_ast.Node]:
        if self._is_symbolic_call(e):

            var_name = e.name
            func_call = e.init.expr.expr

            # Rewrite the function call
            func_call.name.name = "klee_make_symbolic"
            func_call.args.exprs.insert(0, c_ast.UnaryOp(op="&", expr=c_ast.ID(var_name)))
            func_call.args.exprs.append(c_ast.Constant(type="string", value=f'"{var_name}"'))

            # Clear the initializer
            e.init = None

            ret = [e, func_call]

            self._watch_vars.append(var_name)
        elif self._is_watch_call(e):
            assert len(e.args.exprs) == 1 and type(e.args.exprs[0]) is c_ast.Cast
            cast = e.args.exprs[0]
            assert type(cast.expr) is c_ast.UnaryOp and cast.expr.op == "&" and type(cast.expr.expr) is c_ast.ID
            var_name = cast.expr.expr.name

            # Rewrite the function call
            e.name.name = "klee_watch_obj"
            e.args.exprs = [c_ast.UnaryOp(op="&", expr=c_ast.ID(var_name)),
                            c_ast.Constant(type="string", value=f'"{var_name}"')]
            ret = [e]

            self._watch_vars.append(var_name)
        elif self._is_let_call(e):
            assert len(e.args.exprs) == 1

            # Rewrite the function call
            e.name.name = "klee_assume"
            ret = [e]
        else:
            ret = [e]

        return ret

    @staticmethod
    def _is_symbolic_call(e) -> bool:
        if type(e) is c_ast.Decl:
            if type(e.init) is c_ast.UnaryOp and e.init.op == "*":
                if type(e.init.expr) is c_ast.Cast:
                    if type((func_call := e.init.expr.expr)) is c_ast.FuncCall:
                        if type(func_call.name) is c_ast.ID and func_call.name.name == "__symbolic":
                            return True
        return False

    @staticmethod
    def _is_watch_call(e):
        return type(e) is c_ast.FuncCall and type(e.name) is c_ast.ID and e.name.name == "__watch"

    @staticmethod
    def _is_let_call(e):
        return type(e) is c_ast.FuncCall and type(e.name) is c_ast.ID and e.name.name == "__let"

    def generate_klee_driver(self) -> list[str]:
        """
        Generate KLEE driver function.
        :return: list of watched variables
        """

        # Sanity check
        if self._driver_name is None:
            raise RuntimeError("Generate test driver before generating KLEE driver.")
        if not self._test_file:
            raise RuntimeError("Test file is not set")
        if not os.path.exists(self._test_file):
            raise RuntimeError(f"Test file {self._test_file} does not exist")

        self._watch_vars = []

        # if not self._cmake_mode:
        #     self._tmp_test_file = os.path.join(self._tmp_dir.name, os.path.basename(self._test_file))
        #
        #     TEMP_TEST_FILE_PREFIX_LINES = [
        #         '#include "klee_unit.h"',
        #         f'#include "{CATCH_DUMMY_FILENAME}"',
        #         # f'#include "{KLEE_DUMMY_FILENAME}"',
        #     ]
        #
        #     # Append the header to the front of the test file anyway
        #     with open(self._tmp_test_file, "w", encoding="utf-8") as f:
        #         f.write('\n'.join(TEMP_TEST_FILE_PREFIX_LINES) + '\n' + open(self._test_file, "r", encoding="utf-8").read())

        self._tmp_test_file = self._test_file

        # FIXME: -xc++ is required for Apple clang but may not work for other compilers
        self._driver_ast = parse_file(self._tmp_test_file, use_cpp=True,
                                      cpp_args=['-xc++',
                                                f"-I{KLEE_UNIT_INCLUDE}",
                                                f"-I{FAKE_LIBC_INCLUDE}",
                                                f"-include{CATCH_DUMMY_FILENAME}",
                                                f"-include{KLEE_UNIT_HEADER_FILENAME}",
                                                ],
                                      parser=self._parser)  # substitute the macros

        # Lookup the function
        driver_func, start_line, end_line = self._lookup_test_driver_func(self._driver_ast)
        if driver_func is None:
            raise RuntimeError("Cannot find test driver function")
        # start_line -= len(TEMP_TEST_FILE_PREFIX_LINES)

        # Make a deep copy of the AST
        self._driver_func_ast_copy = copy.deepcopy(driver_func)

        # Read the original source code
        with open(self._test_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if start_line > 0:
            self._heading_lines = lines[:start_line]
        else:
            self._heading_lines = None

        driver_func.show()

        # Rewrite the test driver function as main()
        print(driver_func.coord)
        driver_func.decl.name = "main"
        driver_func.decl.type.type.declname = "main"
        driver_func.decl.type.type.type.names = ["int"]
        new_body = []
        for e in driver_func.body.block_items:
            new_body.extend(self._rewrite_statement_to_klee(e))  # change self._watch_vars inside
        driver_func.body.block_items = new_body
        # driver_func.show()

        # Generate KLEE test driver source code
        klee_driver_src = self._generator.visit(driver_func)

        if not self._cmake_mode:
            # Replace the test driver function with KLEE test driver function
            self._klee_driver_file = os.path.join(self._tmp_dir.name, "klee_" + os.path.basename(self._test_file))
            with open(self._klee_driver_file, "w", encoding="utf-8") as f:
                if self._heading_lines is not None:
                    f.writelines(self._heading_lines)
                f.write(f'#include <klee/klee.h>\n')
                f.write(f'#include "{os.path.abspath(self._src_file)}"\n\n')
                f.write(klee_driver_src)
                f.write('void *__symbolic(unsigned long s) { (void) s; return 0; }\n')
                f.write('void __watch(void *ptr) { (void) ptr; }\n')
                f.write('void __let(int cond) { (void) cond; }\n')
                # FIXME: if there is nothing in the AST after the driver, everything will be overwritten
                if end_line is not None:
                    f.writelines(lines[end_line:])

        else:
            # Replace the test driver in place
            self._klee_driver_file = self._test_file
            with open(self._klee_driver_file, "w", encoding="utf-8") as f:
                if self._heading_lines is not None:
                    f.writelines(self._heading_lines)
                f.write(klee_driver_src)
                # FIXME: if there is nothing in the AST after the driver, everything will be overwritten
                if end_line is not None:
                    f.writelines(lines[end_line:])

        return self._watch_vars

    def compile_klee_driver(self) -> (int, str):
        """
        Compile KLEE driver file.
        :return: (clang output, exit code)
        """
        if not self._cmake_mode:
            # Generate LLVM bitcode with clang
            self._bc_filename = os.path.splitext(self._klee_driver_file)[0] + ".bc"
            proc = subprocess.run(
                ["clang",
                 "-I", KLEE_INCLUDE,
                 "-I", KLEE_UNIT_INCLUDE,
                 "-include", CATCH_DUMMY_FILENAME,
                 "-include", KLEE_DUMMY_FILENAME,
                 "-emit-llvm", "-c", "-g", "-O0", self._klee_driver_file,
                 "-o", self._bc_filename],
                capture_output=True,
                universal_newlines=True)

            return proc.returncode, proc.stdout

        else:
            # Generate LLVM bitcode with wllvm
            make_proc = subprocess.run(
                ["make", f"{self._target}"],
                cwd=self._cmake_build_dir,
                env=dict(os.environ, **{
                    "LLVM_COMPILER": "clang",
                }),
                capture_output=True,
                universal_newlines=True)
            if make_proc.returncode != 0:
                return make_proc.returncode, make_proc.stdout

            # Extract the bitcode file
            # FIXME: the executable may not be in the root level of the build directory
            self._bc_filename = os.path.join(self._cmake_build_dir, self._target) + ".bc"
            extract_bc_proc = subprocess.run(
                ["extract-bc", f"{self._target}"],
                cwd=self._cmake_build_dir,
                env=dict(os.environ, **{
                    "LLVM_COMPILER": "clang",
                }),
                shell=True,
                capture_output=True,
                universal_newlines=True)
            return extract_bc_proc.returncode, make_proc.stdout + "\n" + extract_bc_proc.stdout

    def start_klee(self):
        self._klee_output_dir = os.path.join(self._tmp_dir.name, f"klee-out-{self._current_func_name}")
        if os.path.exists(self._klee_output_dir):
            os.system(f"rm -rf {self._klee_output_dir}")

        # Run KLEE
        self._test_cases = []
        try:
            # Use of universal_newlines to treat all newlines as \n for Python's purpose
            self._klee_proc = subprocess.Popen(
                ["klee",
                 "--search=dfs",  # DFS to generate test cases as fast as possible
                 f"-output-dir={self._klee_output_dir}",
                 "--optimize",
                 "--solver-backend=z3",
                 self._bc_filename],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # redirect stderr to stdout
                # universal_newlines=True  # not compatible with os.set_blocking(False)
            )
        except Exception as e:
            raise RuntimeError("Unable to run KLEE. Error: %s" % e)

        # Set non-blocking stdout
        os.set_blocking(self._klee_proc.stdout.fileno(), False)

    def stop_klee(self):
        """
        Stop KLEE and return its return code.
        """
        if self._klee_proc is None:
            return
        self._klee_proc.kill()
        self._klee_proc.wait()
        return self._klee_proc.returncode

    def is_klee_running(self) -> bool:
        if self._klee_proc is None:
            return False
        return self._klee_proc.poll() is None

    def get_klee_return_code(self) -> int:
        if self._klee_proc is None:
            return False
        return self._klee_proc.returncode

    def read_klee_output(self) -> str:
        """
        Non-blocking read of KLEE output.
        """
        read = self._klee_proc.stdout.read()  # os.set_blocking(False) above
        if read:
            return read.decode("utf-8")
        else:
            return ""

    def fetch_new_klee_test_cases(self) -> list[dict]:
        last_test_case_len = len(self._test_cases)

        # Read test cases until no more
        while os.path.exists(
                filename := f"{self._klee_output_dir}/test{str(len(self._test_cases) + 1).zfill(6)}.ktest"):
            # The file may be written by the KLEE at the same time, do error handling

            test_case = {}
            try:
                ktest = KTest.fromfile(filename)
                for name, data in ktest.objects:
                    if name in self._watch_vars:
                        test_case[name] = data
                for name in self._watch_vars:
                    if name not in test_case:
                        VarNotFoundError(f"{name} is not found in {filename}")
            except (VarNotFoundError, KTestError) as e:
                break  # discard the current test case

            # Add the test case
            self._test_cases.append(test_case)

        return self._test_cases[last_test_case_len:]

    def get_all_klee_test_cases(self) -> list[dict]:
        return self._test_cases

    def format_data(self, data: bytes, in_hex: bool) -> str:
        """
        Format the data in hexadecimal.
        """
        UNPACK_FORMAT = {
            1: 'b',
            2: 'h',
            4: 'i',
            8: 'q'
        }
        value = struct.unpack(UNPACK_FORMAT[len(data)], data)[0]
        if in_hex:
            return hex(value)
        else:
            return str(value)

    def remove_test_driver_from_test_file(self):
        with open(self._test_file, "w", encoding="utf-8") as f:
            if self._heading_lines is not None:
                f.writelines(self._heading_lines)

    def _rewrite_statement_to_catch2(self, e, values: dict) -> list[c_ast.Node]:
        if self._is_symbolic_call(e):
            var_name = e.name

            # Rewrite
            e.init = c_ast.Constant(type=e.type.type, value=f'{values[var_name]}')

            ret = [e]

            self._watch_vars.append(var_name)
        elif self._is_watch_call(e):
            assert len(e.args.exprs) == 1 and type(e.args.exprs[0]) is c_ast.Cast
            cast = e.args.exprs[0]
            var_name = cast.expr.expr.name

            # Rewrite the function call
            e.name.name = "REQUIRE"
            e.args.exprs = [c_ast.BinaryOp(op="==", left=c_ast.ID(var_name),
                                           # XXX: int type is not correct, but may not matter for code generation?
                                           right=c_ast.Constant(type=c_ast.IdentifierType(['int']),
                                                                value=f'{values[var_name]}'))]
            ret = [e]

            self._watch_vars.append(var_name)
        elif self._is_let_call(e):
            assert len(e.args.exprs) == 1

            # Rewrite the function call
            e.name.name = "ASSERT"
            ret = [e]
        else:
            ret = [e]

        return ret

    def generate_catch2_case(self, name: str, values: dict):
        """
        Generate a Catch2 test case.
        """
        func = copy.deepcopy(self._driver_func_ast_copy)
        body = []
        for e in func.body.block_items:
            body.extend(self._rewrite_statement_to_catch2(e, values))
        compound = c_ast.Compound(body)

        with open(self._test_file, "a", encoding="utf-8") as f:
            f.write('\nTEST_CASE("' + name + '")\n')
            f.write(self._generator.visit(compound))


if __name__ == '__main__':
    session = KLEEUnitSession()
    # session.set_src_file("/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/tools/klee-unit/examples/lru_cache/cache.h")
    session.set_src_file(
        "/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/tools/klee-unit/examples/get_sign/get_sign.c")

    session.set_test_file(
        "/Users/liuzikai/Documents/Courses/AST/AST-Project/ast-klee/tools/klee-unit/examples/lru_cache/cache_foo_unit.cpp")
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


    session.start_klee(add_test_case)
