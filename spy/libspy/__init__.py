from typing import Any, Optional
import wasmtime as wt
import spy
from spy.llwasm import LLWasmModule, LLWasmInstance, HostModule

# from spy.vm.str import ll_spy_Str_read

SRC = spy.ROOT.join("libspy", "src")
INCLUDE = spy.ROOT.join("libspy", "include")
BUILD = spy.ROOT.join("libspy", "build")
LIBSPY_WASM = spy.ROOT.join("libspy", "build", "wasi", "libspy.wasm")

LLMOD = LLWasmModule(LIBSPY_WASM)


class LibSPyHost(HostModule):
    log: list[str]
    panic_message: Optional[str]

    def __init__(self) -> None:
        self.log = []
        self.panic_message = None

    def _read_str(self, ptr: int) -> str:
        # ptr is const char*
        ba = self.ll.mem.read_cstr(ptr)
        return ba.decode("utf-8")

    # ========== WASM imports ==========

    def env_spy_debug_log(self, ptr: int) -> None:
        s = self._read_str(ptr)
        self.log.append(s)
        print("[log]", s)

    def env_spy_debug_log_i32(self, ptr: int, n: int) -> None:
        s = self._read_str(ptr)
        msg = f"{s} {n}"
        self.log.append(msg)
        print("[log]", msg)

    def env_spy_debug_set_panic_message(self, ptr: int) -> None:
        # ptr is const char*
        ba = self.ll.mem.read_cstr(ptr)
        self.panic_message = ba.decode("utf-8")


class SPyPanicError(Exception):
    """
    Python-level exception raised when a WASM module aborts with a call to
    spy_panic().
    """


class LLSPyInstance(LLWasmInstance):
    """
    A specialized version of LLWasmInstance which automatically link against
    LibSPyHost()
    """

    def __init__(self, llmod: LLWasmModule, hostmods: list[HostModule] = []) -> None:
        self.libspy = LibSPyHost()
        hostmods = [self.libspy] + hostmods
        super().__init__(llmod, hostmods)

    def call(self, name: str, *args: Any) -> Any:
        func = self.get_export(name)
        assert isinstance(func, wt.Func)
        try:
            return func(self.store, *args)
        except wt.Trap:
            if self.libspy.panic_message is not None:
                raise SPyPanicError(self.libspy.panic_message)
            raise
