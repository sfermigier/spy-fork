"""
(Fully) Qualified Names in SPy.

A Qualified Name (QN) locates a function or class inside the source code: it
consists of two parts:

  - module name or `modname`, which is the unique name of the module (possibly
    dotted)

  - attribute name of `attr`, which is the name of the function or class
    inside the module.

In case of closures and generics, you can have multiple objects with the same
QN. To uniquely identify an object inside a live VM, we use a Fully Qualified
Name, or FQN.  If needed, the uniqueness is guaranteed by appending a suffix.

A QN is usually formatted as `modname::attr`: e.g., `a.b.c::foo`.
An FQN is usually formatted as `modname::attr#suffix`, e.g. `a.b.c::foo#0`.
The suffix "" (empty string) is special cased and not shown at all.

The following example explains the difference between QNs and FQNs:

@blue
def make_fn(T):
    def fn(x: T) -> T:
        # QN is 'test::fn'
        return ...
    return fn

fn_i32 = make_fn(i32)  # QN is 'test::fn', FQN is 'test::fn#1'
fn_f64 = make_fn(f64)  # QN is 'test::fn', FQN is 'test::fn#2'

See also SPyVM.get_FQN().
"""

from typing import Optional, Any


class QN:
    modname: str
    attr: str

    def __init__(
        self,
        fullname: Optional[str] = None,
        *,
        modname: Optional[str] = None,
        attr: Optional[str] = None,
    ) -> None:
        if fullname is None:
            assert modname is not None
            assert attr is not None
        else:
            assert modname is None
            assert attr is None
            assert fullname.count("::") == 1
            modname, attr = fullname.split("::")
        #
        self.modname = modname
        self.attr = attr

    def __repr__(self) -> str:
        return f"QN({self.fullname!r})"

    def __str__(self) -> str:
        return self.fullname

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, QN):
            return NotImplemented
        return self.fullname == other.fullname

    def __hash__(self) -> int:
        return hash(self.fullname)

    @property
    def fullname(self) -> str:
        return f"{self.modname}::{self.attr}"


class FQN:
    modname: str
    attr: str
    suffix: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise ValueError(
            "You cannot instantiate an FQN directly. " "Please use vm.get_FQN()"
        )

    @classmethod
    def make(cls, modname: str, attr: str, suffix: str) -> "FQN":
        obj = cls.__new__(cls)
        obj.modname = modname
        obj.attr = attr
        obj.suffix = suffix
        return obj

    @classmethod
    def make_global(cls, modname: str, attr: str) -> "FQN":
        """
        Return the FQN corresponding to a global name.

        Until we have generics, global names are supposed to be unique, so we
        can just use suffix=""
        """
        return cls.make(modname, attr, suffix="")

    @classmethod
    def parse(cls, s: str) -> "FQN":
        if "#" in s:
            assert s.count("#") == 1
            qn, suffix = s.split("#")
        else:
            qn = s
            suffix = ""
        #
        assert qn.count("::") == 1
        modname, attr = qn.split("::")
        return FQN.make(modname=modname, attr=attr, suffix=suffix)

    @property
    def fullname(self) -> str:
        s = f"{self.modname}::{self.attr}"
        if self.suffix != "":
            s += "#" + self.suffix
        return s

    def __repr__(self) -> str:
        return f"FQN({self.fullname!r})"

    def __str__(self) -> str:
        return self.fullname

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FQN):
            return NotImplemented
        return self.fullname == other.fullname

    def __hash__(self) -> int:
        return hash(self.fullname)

    @property
    def c_name(self) -> str:
        """
        Return the C name for the corresponding FQN.

        We need to do a bit of mangling:

          - the modname part can be dotted: we replace '.' with '_'. Note that
            this is potentially unsafe, because e.g. `a.b.c` and `a.b_c` would
            result in the same C name.  This is not ideal but we will solve it
            only if it becomes an actual issue in practice.

          - for separating modname and attr, we use a '$'. Strictly speaking,
            using a '$' in C identifiers is not supported by the standard, but
            in reality it is supported by GCC, clang and MSVC. Again, we will
            think of a different approach if it becomes an actual issue.

        So e.g., the following FQN:
            a.b.c::foo

        Becomes:
            spy_a_b_c$foo
        """
        modname = self.modname.replace(".", "_")
        cn = f"spy_{modname}${self.attr}"
        if self.suffix != "":
            cn += "$" + self.suffix
        return cn

    @property
    def spy_name(self) -> str:
        return f"{self.modname}.{self.attr}"

    def is_module(self) -> bool:
        return self.attr == ""

    def is_object(self) -> bool:
        return self.attr != ""
