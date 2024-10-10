
from spy.fqn import QN
from spy.vm.list import W_List
from spy.vm.object import Annotated, Member
from spy.vm.opimpl import W_OpImpl, W_Value
from spy.vm.registry import ModuleRegistry
from spy.vm.sig import spy_builtin
from spy.vm.vm import SPyVM
from spy.vm.w import W_I32, W_Dynamic, W_Object, W_Str, W_Type

from ..support import CompilerTest, no_C


@no_C
class TestCallOp(CompilerTest):
    SKIP_SPY_BACKEND_SANITY_CHECK = True

    def test_call_instance(self):
        # ========== EXT module for this test ==========
        EXT = ModuleRegistry("ext", "<ext>")

        @EXT.spytype("Adder")
        class W_Adder(W_Object):

            def __init__(self, x: int) -> None:
                self.x = x

            @staticmethod
            def spy_new(vm: "SPyVM", w_cls: W_Type, w_x: W_I32) -> "W_Adder":
                return W_Adder(vm.unwrap_i32(w_x))

            @staticmethod
            def op_CALL(vm: "SPyVM", w_type: W_Type, w_argtypes: W_Dynamic) -> W_OpImpl:
                @spy_builtin(QN("ext::call"))
                def call(vm: "SPyVM", w_obj: W_Adder, w_y: W_I32) -> W_I32:
                    y = vm.unwrap_i32(w_y)
                    res = w_obj.x + y
                    return vm.wrap(res)  # type: ignore

                return W_OpImpl.simple(vm.wrap_func(call))

        # ========== /EXT module for this test =========
        self.vm.make_module(EXT)
        mod = self.compile(
            """
        from ext import Adder

        def foo(x: i32, y: i32) -> i32:
            obj = Adder(x)
            return obj(y)
        """
        )
        x = mod.foo(5, 7)
        assert x == 12

    def test_call_type(self):
        # ========== EXT module for this test ==========
        EXT = ModuleRegistry("ext", "<ext>")

        @EXT.spytype("Point")
        class W_Point(W_Object):
            w_x: Annotated[W_I32, Member("x")]
            w_y: Annotated[W_I32, Member("y")]

            def __init__(self, w_x: W_I32, w_y: W_I32) -> None:
                self.w_x = w_x
                self.w_y = w_y

            @staticmethod
            def meta_op_CALL(
                vm: "SPyVM", w_type: W_Type, w_argtypes: W_Dynamic
            ) -> W_OpImpl:
                @spy_builtin(QN("ext::new"))
                def new(vm: "SPyVM", w_cls: W_Type, w_x: W_I32, w_y: W_I32) -> W_Point:
                    return W_Point(w_x, w_y)

                return W_OpImpl.simple(vm.wrap_func(new))

        # ========== /EXT module for this test =========
        self.vm.make_module(EXT)
        mod = self.compile(
            """
        from ext import Point

        @blue
        def foo(x: i32, y: i32) -> i32:
            p = Point(x, y)
            return p.x * 10 + p.y
        """
        )
        res = mod.foo(3, 6)
        assert res == 36

    def test_spy_new(self):
        # ========== EXT module for this test ==========
        EXT = ModuleRegistry("ext", "<ext>")

        @EXT.spytype("Point")
        class W_Point(W_Object):
            w_x: Annotated[W_I32, Member("x")]
            w_y: Annotated[W_I32, Member("y")]

            def __init__(self, w_x: W_I32, w_y: W_I32) -> None:
                self.w_x = w_x
                self.w_y = w_y

            @staticmethod
            def spy_new(
                vm: "SPyVM", w_cls: W_Type, w_x: W_I32, w_y: W_I32
            ) -> "W_Point":
                return W_Point(w_x, w_y)

        # ========== /EXT module for this test =========
        self.vm.make_module(EXT)
        mod = self.compile(
            """
        from ext import Point

        @blue
        def foo(x: i32, y: i32) -> i32:
            p = Point(x, y)
            return p.x * 10 + p.y
        """
        )
        res = mod.foo(3, 6)
        assert res == 36

    def test_call_method(self):
        # ========== EXT module for this test ==========
        EXT = ModuleRegistry("ext", "<ext>")

        @EXT.spytype("Calc")
        class W_Calc(W_Object):

            def __init__(self, x: int) -> None:
                self.x = x

            @staticmethod
            def spy_new(vm: "SPyVM", w_cls: W_Type, w_x: W_I32) -> "W_Calc":
                return W_Calc(vm.unwrap_i32(w_x))

            @staticmethod
            def op_CALL_METHOD(
                vm: "SPyVM",
                wv_obj: W_Value,
                wv_method: W_Str,
                w_values: W_List[W_Value],
            ) -> W_OpImpl:
                meth = wv_method.blue_unwrap_str(vm)
                if meth == "add":

                    @spy_builtin(QN("ext::meth_add"))
                    def fn(vm: "SPyVM", w_self: W_Calc, w_arg: W_I32) -> W_I32:
                        y = vm.unwrap_i32(w_arg)
                        return vm.wrap(w_self.x + y)  # type: ignore

                    return W_OpImpl.with_values(
                        vm.wrap_func(fn), [wv_obj] + w_values.items_w
                    )

                if meth == "sub":

                    @spy_builtin(QN("ext::meth_sub"))
                    def fn(vm: "SPyVM", w_self: W_Calc, w_arg: W_I32) -> W_I32:
                        y = vm.unwrap_i32(w_arg)
                        return vm.wrap(w_self.x - y)  # type: ignore

                    return W_OpImpl.with_values(
                        vm.wrap_func(fn), [wv_obj] + w_values.items_w
                    )
                return W_OpImpl.NULL

        # ========== /EXT module for this test =========

        self.vm.make_module(EXT)
        mod = self.compile(
            """
        from ext import Calc

        def foo(x: i32, y: i32, z: i32) -> i32:
            obj = Calc(x)
            return obj.add(y) * 10 + obj.sub(z)
        """
        )
        x = mod.foo(5, 1, 2)
        assert x == 63
