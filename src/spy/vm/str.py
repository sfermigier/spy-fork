from typing import TYPE_CHECKING

from spy.fqn import QN
from spy.llwasm import LLWasmInstance
from spy.vm.list import W_List
from spy.vm.object import W_Object, spytype, W_I32
from spy.vm.opimpl import W_OpImpl, W_Value
from spy.vm.sig import spy_builtin

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

W_List.make_prebuilt(W_Value)


def ll_spy_Str_new(ll: LLWasmInstance, s: str) -> int:
    """
    Create a new spy_Str object inside the given LLWasmInstance, and fill it
    with the utf8-encoded content of s.

    Return the corresponding 'spy_Str *'
    """
    utf8 = s.encode("utf-8")
    length = len(utf8)
    ptr = ll.call("spy_str_alloc", length)
    ll.mem.write(ptr + 4, utf8)
    return ptr


@spytype("str")
class W_Str(W_Object):
    """
    An unicode string, internally represented as UTF-8.

    This is basically a 'spy_Str *', i.e. a pointer to a C struct which
    resides in the linear memory of the VM:
        typedef struct {
            size_t length;
            const char utf8[];
        } spy_Str;
    """

    vm: "SPyVM"
    ptr: int

    def __init__(self, vm: "SPyVM", s: str) -> None:
        ptr = ll_spy_Str_new(vm.ll, s)
        self.vm = vm
        self.ptr = ptr

    @staticmethod
    def from_ptr(vm: "SPyVM", ptr: int) -> "W_Str":
        w_res = W_Str.__new__(W_Str)
        w_res.vm = vm
        w_res.ptr = ptr
        return w_res

    def get_length(self) -> int:
        return self.vm.ll.mem.read_i32(self.ptr)

    def get_utf8(self) -> bytes:
        length = self.get_length()
        ba = self.vm.ll.mem.read(self.ptr + 4, length)
        return bytes(ba)

    def _as_str(self) -> str:
        return self.get_utf8().decode("utf-8")

    def __repr__(self) -> str:
        s = self._as_str()
        return f"W_Str({s!r})"

    def spy_unwrap(self, vm: "SPyVM") -> str:
        return self._as_str()

    @staticmethod
    def op_GETITEM(vm: "SPyVM", wv_obj: W_Value, wv_i: W_Value) -> W_OpImpl:
        @spy_builtin(QN("operator::str_getitem"))
        def str_getitem(vm: "SPyVM", w_s: W_Str, w_i: W_I32) -> W_Str:
            assert isinstance(w_s, W_Str)
            assert isinstance(w_i, W_I32)
            ptr_c = vm.ll.call("spy_str_getitem", w_s.ptr, w_i.value)
            return W_Str.from_ptr(vm, ptr_c)

        return W_OpImpl.simple(vm.wrap_func(str_getitem))

    @staticmethod
    def meta_op_CALL(
        vm: "SPyVM", wv_obj: W_Value, w_values: W_List[W_Value]
    ) -> W_OpImpl:
        from spy.vm.b import B

        args_wv = w_values.items_w
        if len(args_wv) == 1 and args_wv[0].w_static_type is B.w_i32:
            wv_i = args_wv[0]
            return W_OpImpl.with_values(vm.wrap_func(int2str), [wv_i])
        return W_OpImpl.NULL


@spy_builtin(QN("builtins::int2str"))
def int2str(vm: "SPyVM", w_i: W_I32) -> W_Str:
    i = vm.unwrap_i32(w_i)
    return vm.wrap(str(i))  # type: ignore
