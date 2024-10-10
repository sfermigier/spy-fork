from typing import TYPE_CHECKING
from spy.fqn import QN
from spy.vm.object import W_Object, spytype, W_Dynamic, W_I32
from spy.vm.sig import spy_builtin
from spy.vm.opimpl import W_OpImpl, W_Value

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM


@spytype("tuple")
class W_Tuple(W_Object):
    """
    This is not the "real" tuple type that we will have in SPy.

    It's a trimmed-down "dynamic" tuple, which can contain an arbitrary number
    of items of arbitrary types. It is meant to be used in blue code, and we
    need it to bootstrap SPy.

    Eventally, it will become a "real" type-safe, generic type.
    """

    items_w: list[W_Object]

    def __init__(self, items_w: list[W_Object]) -> None:
        self.items_w = items_w

    def spy_unwrap(self, vm: "SPyVM") -> tuple:
        return tuple([vm.unwrap(w_item) for w_item in self.items_w])

    @staticmethod
    def op_GETITEM(vm: "SPyVM", wv_obj: W_Value, wv_i: W_Value) -> W_OpImpl:
        return W_OpImpl.simple(vm.wrap_func(tuple_getitem))


@spy_builtin(QN("operator::tuple_getitem"))
def tuple_getitem(vm: "SPyVM", w_tup: W_Tuple, w_i: W_I32) -> W_Dynamic:
    i = vm.unwrap_i32(w_i)
    # XXX bound check?
    return w_tup.items_w[i]
