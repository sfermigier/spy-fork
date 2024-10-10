
from spy.fqn import QN
from spy.vm.b import B
from spy.vm.object import Annotated, Member
from spy.vm.opimpl import W_OpImpl, W_Value
from spy.vm.registry import ModuleRegistry
from spy.vm.sig import spy_builtin
from spy.vm.vm import SPyVM
from spy.vm.w import W_I32, W_Object, W_Str, W_Type, W_Void

from ..support import CompilerTest, no_C


@no_C
class TestAttrOp(CompilerTest):
    SKIP_SPY_BACKEND_SANITY_CHECK = True

    def test_member(self):
        # ========== EXT module for this test ==========
        EXT = ModuleRegistry("ext", "<ext>")

        @EXT.spytype("MyClass")
        class W_MyClass(W_Object):
            w_x: Annotated[W_I32, Member("x")]

            def __init__(self) -> None:
                self.w_x = W_I32(0)

            @staticmethod
            def spy_new(vm: "SPyVM", w_cls: W_Type) -> "W_MyClass":
                return W_MyClass()

        # ========== /EXT module for this test =========
        self.vm.make_module(EXT)
        mod = self.compile(
            """
        from ext import MyClass

        @blue
        def foo():
            obj =  MyClass()
            obj.x = 123
            return obj.x
        """
        )
        x = mod.foo()
        assert x == 123

    def test_getattr_setattr_custom(self):
        # ========== EXT module for this test ==========
        EXT = ModuleRegistry("ext", "<ext>")

        @EXT.spytype("MyClass")
        class W_MyClass(W_Object):

            def __init__(self) -> None:
                self.x = 0

            @staticmethod
            def spy_new(vm: "SPyVM", w_cls: W_Type) -> "W_MyClass":
                return W_MyClass()

            @staticmethod
            def op_GETATTR(vm: "SPyVM", wv_obj: W_Value, wv_attr: W_Value) -> W_OpImpl:
                attr = wv_attr.blue_unwrap_str(vm)
                if attr == "x":

                    @spy_builtin(QN("ext::getx"))
                    def fn(vm: "SPyVM", w_obj: W_MyClass, w_attr: W_Str) -> W_I32:
                        return vm.wrap(w_obj.x)  # type: ignore

                else:

                    @spy_builtin(QN("ext::getany"))
                    def fn(vm: "SPyVM", w_obj: W_MyClass, w_attr: W_Str) -> W_Str:
                        attr = vm.unwrap_str(w_attr)
                        return vm.wrap(attr.upper() + "--42")  # type: ignore

                return W_OpImpl.simple(vm.wrap_func(fn))

            @staticmethod
            def op_SETATTR(
                vm: "SPyVM", wv_obj: W_OpImpl, wv_attr: W_Value, wv_v: W_Value
            ) -> W_OpImpl:
                attr = wv_attr.blue_unwrap_str(vm)
                if attr == "x":

                    @spy_builtin(QN("ext::setx"))
                    def fn(
                        vm: "SPyVM", w_obj: W_MyClass, w_attr: W_Str, w_val: W_I32
                    ) -> W_Void:
                        w_obj.x = vm.unwrap_i32(w_val)
                        return B.w_None

                    return W_OpImpl.simple(vm.wrap_func(fn))
                return W_OpImpl.NULL

        # ========== /EXT module for this test =========

        self.vm.make_module(EXT)
        mod = self.compile(
            """
        from ext import MyClass

        @blue
        def get_hello():
            obj = MyClass()
            return obj.hello

        def get_x() -> i32:
            obj = MyClass()
            return obj.x

        def set_get_x() -> i32:
            obj = MyClass()
            obj.x = 123
            return obj.x
        """
        )
        assert mod.get_hello() == "HELLO--42"
        assert mod.get_x() == 0
        assert mod.set_get_x() == 123
