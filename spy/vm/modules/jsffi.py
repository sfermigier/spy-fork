from typing import TYPE_CHECKING
import struct
from spy.fqn import QN
from spy.vm.b import B
from spy.vm.object import spytype, Member, Annotated
from spy.vm.w import (W_Func, W_Type, W_Object, W_I32, W_F64, W_Void, W_Str,
                      W_Dynamic)
from spy.vm.sig import spy_builtin
from spy.vm.function import W_Func, W_FuncType
from spy.vm.registry import ModuleRegistry

from spy.vm.modules.types import W_TypeDef

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

JSFFI = ModuleRegistry('jsffi', '<jsffi>')

@spytype('JsRef')
class W_JsRef(W_Object):

    @staticmethod
    def op_GETATTR(vm: 'SPyVM', w_type: 'W_Type',
                   w_attr: 'W_Str') -> 'W_Dynamic':
        # this is a horrible hack (see also cwriter.fmt_expr_Call)
        attr = vm.unwrap_str(w_attr)

        @spy_builtin(QN(f'jsffi::getattr_{attr}'))
        def opimpl(vm: 'SPyVM', w_self: W_JsRef, w_attr: W_Str) -> W_JsRef:
            return js_getattr(vm, w_self, w_attr)
        return vm.wrap(opimpl)

    @staticmethod
    def op_SETATTR(vm: 'SPyVM', w_type: 'W_Type', w_attr: 'W_Str',
                   w_vtype: 'W_Type') -> 'W_Dynamic':
        # this is a horrible hack (see also cwriter.fmt_expr_Call)
        attr = vm.unwrap_str(w_attr)

        @spy_builtin(QN(f'jsffi::setattr_{attr}'))
        def opimpl(vm: 'SPyVM', w_self: W_JsRef, w_attr: W_Str,
                   w_val: W_JsRef) -> None:
            js_setattr(vm, w_self, w_attr, w_val)
        return vm.wrap(opimpl)

    @staticmethod
    def op_CALL_METHOD(vm: 'SPyVM', w_type: 'W_Type', w_method: 'W_Str',
                       w_argtypes: 'W_Dynamic') -> 'W_Dynamic':
        argtypes_w = vm.unwrap(w_argtypes)
        n = len(argtypes_w)
        if n == 1:
            return JSFFI.w_call_method_1
        else:
            raise Exception(
                f"unsupported number of arguments for CALL_METHOD: {n}"
            )

@JSFFI.builtin
def call_method_1(vm: 'SPyVM', w_self: W_JsRef, w_method: W_Str,
                  w_arg: W_JsRef) -> W_JsRef:
    return js_call_method_1(w_self, w_method, w_arg)


JSFFI.add('JsRef', W_JsRef._w)

@JSFFI.builtin
def debug(vm: 'SPyVM', w_str: W_Str) -> None:
    s = vm.unwrap_str(w_str)
    print('[JSFFI debug]', s)

@JSFFI.builtin
def init(vm: 'SPyVM') -> None:
    raise NotImplementedError

@JSFFI.builtin
def get_GlobalThis(vm: 'SPyVM') -> W_JsRef:
    raise NotImplementedError

@JSFFI.builtin
def get_Console(vm: 'SPyVM') -> W_JsRef:
    raise NotImplementedError

@JSFFI.builtin
def js_string(vm: 'SPyVM', w_str: W_Str) -> W_JsRef:
    raise NotImplementedError

@JSFFI.builtin
def js_wrap_func(vm: 'SPyVM', w_fn: W_Func) -> W_JsRef:
    raise NotImplementedError

@JSFFI.builtin
def js_call_method_1(vm: 'SPyVM', w_target: W_JsRef,
                     name: W_Str, arg0: W_JsRef) -> W_JsRef:
    raise NotImplementedError

@JSFFI.builtin
def js_getattr(vm: 'SPyVM', w_target: W_JsRef, name: W_Str) -> W_JsRef:
    raise NotImplementedError

@JSFFI.builtin
def js_setattr(vm: 'SPyVM', w_target: W_JsRef,
               name: W_Str, val: W_JsRef) -> None:
    raise NotImplementedError
