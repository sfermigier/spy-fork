from pathlib import Path
from typing import Annotated, Any, no_type_check

import py.path
import typer

from spy.backend.spy import SPyBackend
from spy.cbuild import get_toolchain
from spy.compiler import Compiler, ToolchainType
from spy.errors import SPyError
from spy.magic_py_parse import magic_py_parse
from spy.parser import Parser
from spy.vm.b import B
from spy.vm.function import W_Func, W_FuncType
from spy.vm.vm import SPyVM

app = typer.Typer(pretty_exceptions_enable=False)


def opt(T: type, help: str, names: tuple[str, ...] = ()) -> Any:
    return Annotated[T, typer.Option(*names, help=help)]


def boolopt(help: str, names: tuple[str, ...] = ()) -> Any:
    return opt(bool, help, names)


def do_pyparse(filename: str) -> None:
    with open(filename) as f:
        src = f.read()
    mod = magic_py_parse(src)
    mod.pp()


def dump_spy_mod(vm: SPyVM, modname: str, pretty: bool) -> None:
    fqn_format = "short" if pretty else "full"
    b = SPyBackend(vm, fqn_format=fqn_format)
    print(b.dump_mod(modname))


@no_type_check
@app.command()
def main(
    filename: Path,
    run: boolopt("run the file") = False,
    pyparse: boolopt("dump the Python AST exit") = False,
    parse: boolopt("dump the SPy AST and exit") = False,
    redshift: boolopt("perform redshift and exit") = False,
    cwrite: boolopt("create the .c file and exit") = False,
    g: boolopt("generate debug symbols", names=["-g"]) = False,
    O: opt(int, "optimization level", names=["-O"]) = 0,
    toolchain: opt(
        ToolchainType, "which compiler to use", names=["--toolchain", "-t"]
    ) = "zig",
    pretty: boolopt("prettify redshifted modules") = True,
) -> None:
    try:
        do_main(
            filename, run, pyparse, parse, redshift, cwrite, g, O, toolchain, pretty
        )
    except SPyError as e:
        print(e.format(use_colors=True))


def do_main(
    filename: Path,
    run: bool,
    pyparse: bool,
    parse: bool,
    redshift: bool,
    cwrite: bool,
    debug_symbols: bool,
    opt_level: int,
    toolchain: ToolchainType,
    pretty: bool,
) -> None:
    if pyparse:
        do_pyparse(str(filename))
        return

    if parse:
        parser = Parser.from_filename(str(filename))
        mod = parser.parse()
        mod.pp()
        return

    modname = filename.stem
    builddir = filename.parent
    vm = SPyVM()
    vm.path.append(str(builddir))
    w_mod = vm.import_(modname)

    if run:
        w_main_functype = W_FuncType.parse("def() -> void")
        w_main = w_mod.getattr_maybe("main")
        if w_main is None:
            print("Cannot find function main()")
            return
        vm.typecheck(w_main, w_main_functype)
        assert isinstance(w_main, W_Func)
        w_res = vm.call(w_main, [])
        assert w_res is B.w_None
        return

    vm.redshift()
    if redshift:
        dump_spy_mod(vm, modname, pretty)
        return

    compiler = Compiler(vm, modname, py.path.local(builddir))
    if cwrite:
        t = get_toolchain(toolchain)
        compiler.cwrite(t.TARGET)
    else:
        compiler.cbuild(
            opt_level=opt_level, debug_symbols=debug_symbols, toolchain_type=toolchain
        )


if __name__ == "__main__":
    app()
