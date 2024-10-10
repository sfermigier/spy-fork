from typing import TYPE_CHECKING
from spy.fqn import QN
from spy.vm.w import (
    W_Func,
    W_Object,
    W_Str,
    W_List,
)
from spy.vm.list import W_List
from spy.vm.opimpl import W_OpImpl, W_Value
from spy.vm.sig import spy_builtin
from spy.vm.registry import ModuleRegistry

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

JSFFI = ModuleRegistry("jsffi", "<jsffi>")


@JSFFI.spytype("JsRef")
class W_JsRef(W_Object):

    @staticmethod
    def op_GETATTR(vm: "SPyVM", wv_obj: W_Value, wv_attr: W_Value) -> W_OpImpl:
        attr = wv_attr.blue_unwrap_str(vm)

        # this is a horrible hack (see also cwriter.fmt_expr_Call)
        @spy_builtin(QN(f"jsffi::getattr_{attr}"))
        def fn(vm: "SPyVM", w_self: W_JsRef, w_attr: W_Str) -> W_JsRef:
            return js_getattr(vm, w_self, w_attr)

        return W_OpImpl.simple(vm.wrap_func(fn))

    @staticmethod
    def op_SETATTR(
        vm: "SPyVM", wv_obj: W_Value, wv_attr: W_Value, wv_v: W_Value
    ) -> W_OpImpl:
        attr = wv_attr.blue_unwrap_str(vm)

        # this is a horrible hack (see also cwriter.fmt_expr_Call)
        @spy_builtin(QN(f"jsffi::setattr_{attr}"))
        def fn(vm: "SPyVM", w_self: W_JsRef, w_attr: W_Str, w_val: W_JsRef) -> None:
            js_setattr(vm, w_self, w_attr, w_val)

        return W_OpImpl.simple(vm.wrap_func(fn))

    @staticmethod
    def op_CALL_METHOD(
        vm: "SPyVM", wv_obj: W_Value, wv_method: W_Value, w_values: W_List[W_Value]
    ) -> W_OpImpl:
        args_wv = w_values.items_w
        n = len(args_wv)
        if n == 1:
            return W_OpImpl.simple(JSFFI.w_call_method_1)
        raise Exception(f"unsupported number of arguments for CALL_METHOD: {n}")


@JSFFI.builtin
def call_method_1(
    vm: "SPyVM", w_self: W_JsRef, w_method: W_Str, w_arg: W_JsRef
) -> W_JsRef:
    return js_call_method_1(w_self, w_method, w_arg)


@JSFFI.builtin
def debug(vm: "SPyVM", w_str: W_Str) -> None:
    s = vm.unwrap_str(w_str)
    print("[JSFFI debug]", s)


@JSFFI.builtin
def init(vm: "SPyVM") -> None:
    raise NotImplementedError


@JSFFI.builtin
def get_GlobalThis(vm: "SPyVM") -> W_JsRef:
    raise NotImplementedError


@JSFFI.builtin
def get_Console(vm: "SPyVM") -> W_JsRef:
    raise NotImplementedError


@JSFFI.builtin
def js_string(vm: "SPyVM", w_str: W_Str) -> W_JsRef:
    raise NotImplementedError


@JSFFI.builtin
def js_wrap_func(vm: "SPyVM", w_fn: W_Func) -> W_JsRef:
    raise NotImplementedError


@JSFFI.builtin
def js_call_method_1(
    vm: "SPyVM", w_target: W_JsRef, name: W_Str, arg0: W_JsRef
) -> W_JsRef:
    raise NotImplementedError


@JSFFI.builtin
def js_getattr(vm: "SPyVM", w_target: W_JsRef, name: W_Str) -> W_JsRef:
    raise NotImplementedError


@JSFFI.builtin
def js_setattr(vm: "SPyVM", w_target: W_JsRef, name: W_Str, val: W_JsRef) -> None:
    raise NotImplementedError
