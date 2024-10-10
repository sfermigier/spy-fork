from typing import Optional, Literal, TYPE_CHECKING, Any
from dataclasses import dataclass, KW_ONLY, replace
from spy.fqn import FQN
from spy.location import Loc
from spy.errors import SPyScopeError
from spy.textbuilder import ColorFormatter

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

Color = Literal["red", "blue"]


@dataclass
class Symbol:
    name: str
    color: Color
    _: KW_ONLY
    loc: Loc  # where the symbol is defined, in the source code
    type_loc: Loc  # loc of the TYPE of the symbols

    # level indicates in which scope the symbol resides:
    #   0: this Symbol is defined in the scope corresponding to
    #      the curreny SymTable (i.e., it's a "local variable")
    #   1: this is the most immediate outer scope
    #   2: the outer-outer, etc.
    #
    # E.g., for a module-level funcdef, we have three levels:
    #   * 0: local variables inside the funcdef
    #   * 1: module-level scope
    #   * 2: builtins
    level: int
    fqn: FQN | None = None

    def replace(self, **kwargs: Any) -> "Symbol":
        return replace(self, **kwargs)

    @property
    def is_local(self) -> bool:
        return self.level == 0

    @property
    def is_global(self) -> bool:
        return self.level != 0 and self.fqn is not None


class SymTable:
    name: str  # just for debugging
    _symbols: dict[str, Symbol]

    def __init__(self, name: str) -> None:
        self.name = name
        self._symbols = {}

    @classmethod
    def from_builtins(cls, vm: "SPyVM") -> "SymTable":
        scope = cls("builtins")
        loc = Loc(
            filename="<builtins>", line_start=0, line_end=0, col_start=0, col_end=0
        )
        builtins_mod = vm.modules_w["builtins"]
        for fqn, w_obj in builtins_mod.items_w():
            sym = Symbol(fqn.attr, "blue", loc=loc, type_loc=loc, level=0, fqn=fqn)
            scope.add(sym)
        return scope

    def __repr__(self) -> str:
        return f"<SymTable '{self.name}'>"

    def pp(self) -> None:
        color = ColorFormatter(use_colors=True)
        name = color.set("green", self.name)
        print(f"<symbol table '{name}'>")
        symbols = sorted(self._symbols.values(), key=lambda sym: (sym.level, sym.color))
        for sym in symbols:
            sym_name = color.set(sym.color, f"{sym.name:10s}")
            fqn = ""
            if sym.fqn:
                fqn = f" => {sym.fqn}"
            print(f"    [{sym.level}] {sym.color:4s} {sym_name} {fqn}")

    def add(self, sym: Symbol) -> None:
        self._symbols[sym.name] = sym

    def lookup(self, name: str) -> Symbol:
        return self._symbols[name]

    def lookup_maybe(self, name: str) -> Symbol | None:
        return self._symbols.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._symbols
