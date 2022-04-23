# -*- encoding: utf-8 -*-

import sys
from pycparser import c_parser, c_ast, c_generator
from typing import Optional
from enum import Enum
from dataclasses import dataclass, field


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

        self._ast: Optional[c_ast.FileAST] = None
        self._func_decls: Optional[dict[str, c_ast.FuncDecl]] = None
        self._current_func_name: Optional[str] = None
        self._args: Optional[dict[str, _ArgumentInfo]] = None
        self._watch_ret = False

        self.reload_src()

    def reload_src(self) -> None:
        self._ast = self._parser.parse(open(self._src_file, "r", encoding="utf-8").read())

    def analyze_src(self) -> dict[str, str]:
        """
        Analyze the source file.
        :return: dict of {function name: function signature}
        """
        if self._ast is None:
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
        v.visit(self._ast)
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

        with open(self._test_file, "a", encoding="utf-8") as f:
            f.write(driver_src)

        return driver_src
