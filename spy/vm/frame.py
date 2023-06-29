"""
Frame object.

The Frame class contains the logic to execute the SPy IR. The core of the VM
is here.

This is a stupidly simple and infefficient VM. Tons of optimizations could be
made but, for the time being, we don't care about performance.

The code contains many assert()s to do various sanity checks at runtime, for
example that the runtime type of locals matches the declared compile time
type, or that the stack has only one element on it when we execute 'return'.

In theory, many of these properties could be verified offline by writing a
bytecode verifier, but we don't care for now. The bytecode is generated by our
codegen, so the point of the assert()s is mostly to catch bugs in it.
"""

from typing import TYPE_CHECKING, Any
from spy.vm.object import W_Object, W_Type, W_i32
from spy.vm.codeobject import W_CodeObject
from spy.vm.varstorage import VarStorage
if TYPE_CHECKING:
    from spy.vm.vm import SPyVM


class Frame:
    vm: 'SPyVM'
    w_code: W_CodeObject
    pc: int  # program counter
    stack: list[W_Object]
    locals: VarStorage

    def __init__(self, vm: 'SPyVM', w_code: W_Object, globals: VarStorage) -> None:
        assert isinstance(w_code, W_CodeObject)
        self.vm = vm
        self.w_code = w_code
        self.globals = globals
        self.locals = VarStorage(vm, f"'{w_code.name} locals'", w_code.locals_w_types)
        self.pc = 0
        self.stack = []

    def push(self, w_value: W_Object) -> None:
        assert isinstance(w_value, W_Object)
        self.stack.append(w_value)

    def pop(self) -> W_Object:
        return self.stack.pop()

    def init_arguments(self, args_w: list[W_Object]) -> None:
        params = self.w_code.w_functype.params
        assert len(args_w) == len(params)
        for param, w_arg in zip(params, args_w):
            self.locals.set(param.name, w_arg)

    def run(self, args_w: list[W_Object]) -> W_Object:
        self.init_arguments(args_w)
        while True:
            op = self.w_code.body[self.pc]
            # 'return' is special, handle it explicitly
            if op.name == 'return':
                assert len(self.stack) == 1
                w_result = self.pop()
                assert self.vm.is_compatible_type(
                    w_result,
                    self.w_code.w_functype.w_restype)
                return w_result
            else:
                meth_name = f'op_{op.name}'
                meth = getattr(self, meth_name, None)
                if meth is None:
                    raise NotImplementedError(meth_name)
                meth(*op.args)
                self.pc += 1

    def op_const_load(self, w_const: W_Object) -> None:
        self.push(w_const)

    def _exec_op_i32_binop(self, func: Any) -> None:
        w_b = self.pop()
        w_a = self.pop()
        assert isinstance(w_a, W_i32)
        assert isinstance(w_b, W_i32)
        a = self.vm.unwrap(w_a)
        b = self.vm.unwrap(w_b)
        c = func(a, b)
        w_c = self.vm.wrap(c)
        self.push(w_c)

    def op_i32_add(self) -> None:
        self._exec_op_i32_binop(lambda a, b: a + b)

    def op_i32_sub(self) -> None:
        self._exec_op_i32_binop(lambda a, b: a - b)

    def op_i32_mul(self) -> None:
        self._exec_op_i32_binop(lambda a, b: a * b)

    def op_local_get(self, varname: str) -> None:
        w_value = self.locals.get(varname)
        self.push(w_value)

    def op_local_set(self, varname: str) -> None:
        w_value = self.pop()
        self.locals.set(varname, w_value)

    def op_global_get(self, varname: str) -> None:
        w_value = self.globals.get(varname)
        self.push(w_value)

    def op_global_set(self, varname: str) -> None:
        w_value = self.pop()
        self.globals.set(varname, w_value)

    def op_call(self, funcname: str, argcount: int) -> None:
        w_func = self.globals.get(funcname)
        args_w = []
        for i in range(argcount):
            args_w.append(self.pop())
        args_w.reverse()
        w_res = self.vm.call_function(w_func, args_w)
        self.push(w_res)
