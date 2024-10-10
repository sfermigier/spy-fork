import typing
from typing import Optional, Iterator, Any, Literal
import pprint
import ast as py_ast
import dataclasses
from dataclasses import dataclass, field
from spy.fqn import FQN
from spy.location import Loc
from spy.irgen.symtable import SymTable, Color
from spy.util import extend

AnyNode = typing.Union[py_ast.AST, "Node"]
VarKind = typing.Literal["const", "var"]


@extend(py_ast.AST)
class AST:
    """
    monkey patch py_ast.AST to add a loc property. See also the comments in
    stubs/_ast.pyi
    """

    _loc = None

    @property
    def loc(self) -> Loc:
        if self._loc is not None:
            return self._loc
        raise ValueError(f"{self.__class__.__name__} does not have a location")

    def compute_all_locs(self, filename: str) -> None:
        """
        Compute .loc for itself and all its descendants.
        """
        for py_node in py_ast.walk(self):  # type: ignore
            if hasattr(py_node, "lineno"):
                assert py_node.end_lineno is not None
                assert py_node.end_col_offset is not None
                loc = Loc(
                    filename=filename,
                    line_start=py_node.lineno,
                    line_end=py_node.end_lineno,
                    col_start=py_node.col_offset,
                    col_end=py_node.end_col_offset,
                )
                py_node._loc = loc

    @typing.no_type_check
    def pp(self, *, hl=None) -> None:
        import spy.ast_dump

        spy.ast_dump.pprint(self, hl=hl)


del AST

# we want all nodes to compare by *identity* and be hashable, because e.g. we
# put them in dictionaries inside the typechecker. So, we must use eq=False ON
# ALL AST NODES.
#
# Ideally, I would like to do the following:
#     def astnode():
#         return dataclass (eq=False)
#
#     @astnode
#     class Node:
#         ...
#
# But we can't because this pattern is not understood by mypy.


@dataclass(eq=False)
class Node:

    def pp(self, hl: Any = None) -> None:
        import spy.ast_dump

        spy.ast_dump.pprint(self, hl=hl)

    @typing.no_type_check
    def ppc(self) -> None:
        """
        Like .pp(), but also copies the output in the clipboard. Useful for
        copy&paste expected output into your editor.
        """
        import spy.ast_dump

        spy.ast_dump.pprint(self, copy_to_clipboard=True)

    def replace(self, **kwargs: Any) -> Any:
        return dataclasses.replace(self, **kwargs)

    def walk(self, cls: Optional[type] = None) -> Iterator["Node"]:
        if cls is None or isinstance(self, cls):
            yield self
        for node in self.get_children():
            yield from node.walk(cls)

    def get_children(self) -> Iterator["Node"]:
        for f in self.__dataclass_fields__.values():
            value = getattr(self, f.name)
            if isinstance(value, Node):
                yield value
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Node):
                        yield item

    def visit(self, prefix: str, visitor: Any, *args: Any) -> None:
        """
        Generic visitor algorithm.

        For each node of class Foo, we try to locate and call a method called
        {prefix}_Foo on the visitor object:

          - if it exists, it is called. It is responsibility of the method to
            visit its children, if wanted

          - if it doesn't exist, we recurively visit its children
        """
        cls = self.__class__.__name__
        methname = f"{prefix}_{cls}"
        meth = getattr(visitor, methname, None)
        if meth:
            meth(self, *args)
        else:
            for node in self.get_children():
                node.visit(prefix, visitor, *args)


@dataclass(eq=False)
class Module(Node):
    filename: str
    decls: list["Decl"]

    def get_funcdef(self, name: str) -> "FuncDef":
        """
        Search for the FuncDef with the given name.
        """
        for decl in self.decls:
            if isinstance(decl, GlobalFuncDef) and decl.funcdef.name == name:
                return decl.funcdef
        raise KeyError(name)


class Decl(Node):
    pass


@dataclass(eq=False)
class GlobalFuncDef(Decl):
    loc: Loc = field(repr=False)
    funcdef: "FuncDef"


@dataclass(eq=False)
class GlobalVarDef(Decl):
    vardef: "VarDef"
    assign: "Assign"

    @property
    def loc(self) -> Loc:
        return self.vardef.loc


@dataclass(eq=False)
class Import(Decl):
    loc: Loc = field(repr=False)
    loc_asname: Loc
    fqn: FQN
    asname: str


# ====== Expr hierarchy ======


@dataclass(eq=False)
class Expr(Node):
    """
    Operator precedence table, see
    https://docs.python.org/3/reference/expressions.html#operator-precedence

    PREC  OPERATOR
    17    (expr...),  [expr...], {key: value...}, {expr...}
    16    x[index], x[index:index], x(arguments...), x.attribute
    15    await x
    14    **
    13    +x, -x, ~x
    12    *, @, /, //, %
    11    +, -
    10    <<, >>
     9    &
     8    ^
     7    |
     6    in, not in, is, is not, <, <=, >, >=, !=, ==
     5    not x
     4    and
     3    or
     2    if – else
     1    lambda
     0    :=
    """

    # precedence must be overriden by subclasses. The weird type comment is
    # needed to make mypy happy
    precedence = "<Expr.precedence not set>"  # type: int # type: ignore
    loc: Loc = field(repr=False)

    def is_const(self) -> bool:
        return isinstance(self, Constant)


@dataclass(eq=False)
class Name(Expr):
    precedence = 100  # the highest
    id: str


@dataclass(eq=False)
class Auto(Expr):
    precedence = 100  # the highest


@dataclass(eq=False)
class Constant(Expr):
    precedence = 100  # the highest
    value: object


@dataclass(eq=False)
class GetItem(Expr):
    precedence = 16
    value: Expr
    index: Expr


@dataclass(eq=False)
class List(Expr):
    precedence = 17
    items: list[Expr]


@dataclass(eq=False)
class Tuple(Expr):
    precedence = 17
    items: list[Expr]


@dataclass(eq=False)
class Call(Expr):
    precedence = 16
    func: Expr
    args: list[Expr]


@dataclass(eq=False)
class CallMethod(Expr):
    precedence = 17  # higher than GetAttr
    target: Expr
    method: str
    args: list[Expr]


@dataclass(eq=False)
class GetAttr(Expr):
    precedence = 16
    value: Expr
    attr: str


# ====== BinOp sub-hierarchy ======


@dataclass(eq=False)
class BinOp(Expr):
    op = ""
    left: Expr
    right: Expr


@dataclass(eq=False)
class Eq(BinOp):
    precedence = 6
    op = "=="


@dataclass(eq=False)
class NotEq(BinOp):
    precedence = 6
    op = "!="


@dataclass(eq=False)
class Lt(BinOp):
    precedence = 6
    op = "<"


@dataclass(eq=False)
class LtE(BinOp):
    precedence = 6
    op = "<="


@dataclass(eq=False)
class Gt(BinOp):
    precedence = 6
    op = ">"


@dataclass(eq=False)
class GtE(BinOp):
    precedence = 6
    op = ">="


@dataclass(eq=False)
class Is(BinOp):
    precedence = 6
    op = "is"


@dataclass(eq=False)
class IsNot(BinOp):
    precedence = 6
    op = "is not"


@dataclass(eq=False)
class In(BinOp):
    precedence = 6
    op = "in"


@dataclass(eq=False)
class NotIn(BinOp):
    precedence = 6
    op = "not in"


@dataclass(eq=False)
class Add(BinOp):
    precedence = 11
    op = "+"


@dataclass(eq=False)
class Sub(BinOp):
    precedence = 11
    op = "-"


@dataclass(eq=False)
class Mul(BinOp):
    precedence = 12
    op = "*"


@dataclass(eq=False)
class Div(BinOp):
    precedence = 12
    op = "/"


@dataclass(eq=False)
class FloorDiv(BinOp):
    precedence = 12
    op = "//"


@dataclass(eq=False)
class Mod(BinOp):
    precedence = 12
    op = "%"


@dataclass(eq=False)
class Pow(BinOp):
    precedence = 14
    op = "**"


@dataclass(eq=False)
class LShift(BinOp):
    precedence = 10
    op = "<<"


@dataclass(eq=False)
class RShift(BinOp):
    precedence = 10
    op = ">>"


@dataclass(eq=False)
class BitXor(BinOp):
    precedence = 8
    op = "^"


@dataclass(eq=False)
class BitOr(BinOp):
    precedence = 7
    op = "|"


@dataclass(eq=False)
class BitAnd(BinOp):
    precedence = 9
    op = "&"


@dataclass(eq=False)
class MatMul(BinOp):
    precedence = 12
    op = "@"


# ====== UnaryOp sub-hierarchy ======


@dataclass(eq=False)
class UnaryOp(Expr):
    op = ""
    value: Expr


@dataclass(eq=False)
class UnaryPos(UnaryOp):
    precedence = 13
    op = "+"


@dataclass(eq=False)
class UnaryNeg(UnaryOp):
    precedence = 13
    op = "-"


@dataclass(eq=False)
class Invert(UnaryOp):
    precedence = 13
    op = "~"


@dataclass(eq=False)
class Not(UnaryOp):
    precedence = 5
    op = "not"


# ====== Stmt hierarchy ======


@dataclass(eq=False)
class Stmt(Node):
    loc: Loc = field(repr=False)


@dataclass(eq=False)
class FuncArg(Node):
    loc: Loc = field(repr=False)
    name: str
    type: "Expr"


@dataclass(eq=False)
class FuncDef(Stmt):
    loc: Loc = field(repr=False)
    color: Color
    name: str
    args: list[FuncArg]
    return_type: "Expr"
    body: list["Stmt"]
    symtable: Any = field(repr=False, default=None)

    @property
    def prototype_loc(self) -> Loc:
        """
        Return the Loc which corresponds to the func prototype, i.e. from the
        'def' until the return type.
        """
        return Loc.combine(self.loc, self.return_type.loc)


@dataclass(eq=False)
class Pass(Stmt):
    pass


@dataclass(eq=False)
class Return(Stmt):
    value: Expr


@dataclass(eq=False)
class VarDef(Stmt):
    kind: VarKind
    name: str
    type: Expr


@dataclass(eq=False)
class StmtExpr(Stmt):
    """
    An expr used as a statement
    """

    value: Expr


@dataclass(eq=False)
class Assign(Stmt):
    target_loc: Loc = field(repr=False)
    target: str
    value: Expr


@dataclass(eq=False)
class UnpackAssign(Stmt):
    target_locs: list[Loc] = field(repr=False)
    targets: list[str]
    value: Expr

    @property
    def targlocs(self) -> list[tuple[str, Loc]]:
        return list(zip(self.targets, self.target_locs))


@dataclass(eq=False)
class SetAttr(Stmt):
    target_loc: Loc = field(repr=False)
    target: Expr
    attr: str
    value: Expr


@dataclass(eq=False)
class SetItem(Stmt):
    target_loc: Loc = field(repr=False)
    target: Expr
    index: Expr
    value: Expr


@dataclass(eq=False)
class If(Stmt):
    test: Expr
    then_body: list[Stmt]
    else_body: list[Stmt]

    @property
    def has_else(self) -> bool:
        return len(self.else_body) > 0


@dataclass(eq=False)
class While(Stmt):
    test: Expr
    body: list[Stmt]


# ====== Doppler-specific nodes ======
#
# The following nodes are special: they are never generated by the parser, but
# only by the doppler during redshift. In other words, they are not part of
# the proper AST-which-represent-the-syntax-of-the-language, but they are part
# of the AST-which-we-use-as-IR


@dataclass(eq=False)
class FQNConst(Expr):
    precedence = 100  # the highest
    fqn: FQN
