from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from spy.ast import Color
from spy.fqn import QN
from spy.vm.object import W_Object, spytype
from spy.vm.sig import spy_builtin, SPyBuiltin


class ModuleRegistry:
    """
    Keep track of all the objects which belong to a certain module.

    At startup, the `vm` will create a W_Module out of it.
    """

    modname: str
    filepath: str
    content: list[tuple[QN, W_Object]]

    def __init__(self, modname: str, filepath: str) -> None:
        self.modname = modname
        self.filepath = filepath
        self.content = []

    if TYPE_CHECKING:

        def __getattr__(self, attr: str) -> Any:
            """
            Workaround for mypy blindness.

            When we do X.add('foo', ...), it becomes available as X.w_foo, but
            mypy obviously doesn't know. This is a big problem in particular
            for the B (builtins) module, since we use B.w_i32, B.w_object,
            etc. everywhere.

            By using this fake __getattr__, mypy will never complain about
            missing attributes on ModuleRegistry (which is a bit suboptimal,
            but well...)
            """

    def add(self, attr: str, w_obj: W_Object) -> None:
        qn = QN(modname=self.modname, attr=attr)
        setattr(self, f"w_{attr}", w_obj)
        self.content.append((qn, w_obj))

    def spytype(self, name: str) -> Callable:
        """
        Register a type on the module.

        In practice:
            @MOD.spytype('Foo')
            class W_Foo(W_Object):
                ...

        is equivalent to:
            @spytype('Foo')
            class W_Foo(W_Object):
                ...
            MOD.add('Foo', W_Foo._w)
        """

        def decorator(pyclass: type[W_Object]) -> type[W_Object]:
            W_class = spytype(name)(pyclass)
            self.add(name, W_class._w)
            return W_class

        return decorator

    def builtin(self, pyfunc: Callable | None = None, *, color: Color = "red") -> Any:
        """
        Register a builtin function on the module. We support two different
        syntaxes:

        @MOD.builtin
        def foo(): ...

        @MOD.builtin(color='...')
        def foo(): ...
        """

        def decorator(pyfunc: Callable) -> SPyBuiltin:
            attr = pyfunc.__name__
            qn = QN(modname=self.modname, attr=attr)
            # apply the @spy_builtin decorator to pyfunc
            spyfunc = spy_builtin(qn, color=color)(pyfunc)
            w_func = spyfunc._w
            setattr(self, f"w_{attr}", w_func)
            self.content.append((qn, w_func))
            return spyfunc

        if pyfunc is None:
            return decorator
        return decorator(pyfunc)
