import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from spy.ast import Color
from spy.fqn import QN
from spy.vm.function import FuncParam, W_FuncType, W_BuiltinFunc
from spy.vm.object import W_Object, W_Dynamic, w_DynamicType, W_Void

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

# we cannot import B due to circular imports, let's fake it
B_w_dynamic = w_DynamicType
B_w_Void = W_Void._w


def is_W_class(x: Any) -> bool:
    return isinstance(x, type) and issubclass(x, W_Object)


def to_spy_FuncParam(p: Any) -> FuncParam:
    if p.name.startswith("w_"):
        name = p.name[2:]
    else:
        name = p.name
    pyclass = p.annotation
    if pyclass is W_Dynamic:
        return FuncParam(name, B_w_dynamic)
    if issubclass(pyclass, W_Object):
        return FuncParam(name, pyclass._w)
    raise ValueError(f"Invalid param: '{p}'")


def functype_from_sig(fn: Callable, color: Color) -> W_FuncType:
    sig = inspect.signature(fn)
    params = list(sig.parameters.values())
    if len(params) == 0:
        msg = "The first param should be 'vm: SPyVM'. Got nothing"
        raise ValueError(msg)
    if params[0].name != "vm" or params[0].annotation != "SPyVM":
        msg = f"The first param should be 'vm: SPyVM'. Got '{params[0]}'"
        raise ValueError(msg)

    func_params = [to_spy_FuncParam(p) for p in params[1:]]
    ret = sig.return_annotation
    if ret is None:
        w_restype = B_w_Void
    elif ret is W_Dynamic:
        w_restype = B_w_dynamic
    elif is_W_class(ret):
        w_restype = ret._w
    else:
        raise ValueError(f"Invalid return type: '{sig.return_annotation}'")

    return W_FuncType(func_params, w_restype, color=color)


def spy_builtin(qn: QN, color: Color = "red") -> Callable:
    """
    Decorator to make an interp-level function wrappable by the VM.

    Example of usage:

        @spy_builtin(QN("foo::hello"))
        def hello(vm: 'SPyVM', w_x: W_I32) -> W_Str:
            ...

        w_hello = vm.wrap(hello)
        assert isinstance(w_hello, W_BuiltinFunc)
        assert w_hello.qn == QN("foo::hello")

    The w_functype of the wrapped function is automatically computed by
    inspectng the signature of the interp-level function. The first parameter
    MUST be 'vm'.

    Note that the decorated object is no longer the original function, but an
    instance of SPyBuiltin: among the other things, this ensures that blue
    calls are correctly cached.
    """

    def decorator(fn: Callable) -> SPyBuiltin:
        return SPyBuiltin(fn, qn, color)

    return decorator


class SPyBuiltin:
    fn: Callable
    _w: W_BuiltinFunc

    def __init__(self, fn: Callable, qn: QN, color: Color) -> None:
        self.fn = fn
        w_functype = functype_from_sig(fn, color)
        self._w = W_BuiltinFunc(w_functype, qn, fn)

    @property
    def w_functype(self) -> W_FuncType:
        return self._w.w_functype

    def __call__(self, vm: "SPyVM", *args: W_Object) -> W_Object:
        args_w = list(args)
        return vm.call(self._w, args_w)
