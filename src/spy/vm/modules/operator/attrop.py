from typing import TYPE_CHECKING, Literal, no_type_check
from spy.fqn import QN
from spy.vm.b import B
from spy.vm.object import W_Type, W_Void
from spy.vm.str import W_Str
from spy.vm.sig import spy_builtin
from spy.vm.opimpl import W_OpImpl, W_Value

from . import OP

if TYPE_CHECKING:
    from spy.vm.vm import SPyVM

OpKind = Literal["get", "set"]


def unwrap_attr_maybe(vm: "SPyVM", wv_attr: W_Value) -> str:
    if wv_attr.is_blue() and wv_attr.w_static_type is B.w_str:
        return vm.unwrap_str(wv_attr.w_blueval)
    return "<unknown>"


@OP.builtin(color="blue")
def GETATTR(vm: "SPyVM", wv_obj: W_Value, wv_attr: W_Value) -> W_OpImpl:
    from spy.vm.typechecker import typecheck_opimpl

    attr = unwrap_attr_maybe(vm, wv_attr)
    w_opimpl = _get_GETATTR_opimpl(vm, wv_obj, wv_attr, attr)
    typecheck_opimpl(
        vm,
        w_opimpl,
        [wv_obj, wv_attr],
        dispatch="single",
        errmsg="type `{0}` has no attribute '%s'" % attr,
    )
    return w_opimpl


def _get_GETATTR_opimpl(
    vm: "SPyVM", wv_obj: W_Value, wv_attr: W_Value, attr: str
) -> W_OpImpl:
    w_type = wv_obj.w_static_type
    pyclass = w_type.pyclass
    if w_type is B.w_dynamic:
        raise NotImplementedError("implement me")
    if attr in pyclass.__spy_members__:
        return opimpl_member("get", vm, w_type, attr)
    if pyclass.has_meth_overriden("op_GETATTR"):
        return pyclass.op_GETATTR(vm, wv_obj, wv_attr)

    # until commit fc4ff1b we had special logic for typedef. At some point we
    # either need to resume it or kill typedef entirely.
    return W_OpImpl.NULL


@OP.builtin(color="blue")
def SETATTR(vm: "SPyVM", wv_obj: W_Value, wv_attr: W_Value, wv_v: W_Value) -> W_OpImpl:
    from spy.vm.typechecker import typecheck_opimpl

    attr = unwrap_attr_maybe(vm, wv_attr)
    w_opimpl = _get_SETATTR_opimpl(vm, wv_obj, wv_attr, wv_v, attr)
    errmsg = "type `{0}` does not support assignment to attribute '%s'" % attr
    typecheck_opimpl(
        vm, w_opimpl, [wv_obj, wv_attr, wv_v], dispatch="single", errmsg=errmsg
    )
    return w_opimpl


def _get_SETATTR_opimpl(
    vm: "SPyVM", wv_obj: W_Value, wv_attr: W_Value, wv_v: W_Value, attr: str
) -> W_OpImpl:
    w_type = wv_obj.w_static_type
    pyclass = w_type.pyclass
    if w_type is B.w_dynamic:
        return W_OpImpl.simple(OP.w_dynamic_setattr)
    if attr in pyclass.__spy_members__:
        return opimpl_member("set", vm, w_type, attr)
    if pyclass.has_meth_overriden("op_SETATTR"):
        return pyclass.op_SETATTR(vm, wv_obj, wv_attr, wv_v)

    # until commit fc4ff1b we had special logic for typedef. At some point we
    # either need to resume it or kill typedef entirely.
    return W_OpImpl.NULL


def opimpl_member(kind: OpKind, vm: "SPyVM", w_type: W_Type, attr: str) -> W_OpImpl:
    pyclass = w_type.pyclass
    member = pyclass.__spy_members__[attr]
    W_Class = pyclass
    W_Value = member.w_type.pyclass
    field = member.field  # the interp-level name of the attr (e.g, 'w_x')

    # XXX QNs are slightly wrong because they uses the type name as the
    # modname. We need to rethink how QNs are computed

    if kind == "get":

        @no_type_check
        @spy_builtin(QN(modname=w_type.name, attr=f"__get_{attr}__"))
        def opimpl_get(vm: "SPyVM", w_obj: W_Class, w_attr: W_Str) -> W_Value:
            return getattr(w_obj, field)

        return W_OpImpl.simple(vm.wrap_func(opimpl_get))

    if kind == "set":

        @no_type_check
        @spy_builtin(QN(modname=w_type.name, attr=f"__set_{attr}__"))
        def opimpl_set(
            vm: "SPyVM", w_obj: W_Class, w_attr: W_Str, w_val: W_Value
        ) -> W_Void:
            setattr(w_obj, field, w_val)

        return W_OpImpl.simple(vm.wrap_func(opimpl_set))

    assert False, f"Invalid OpKind: {kind}"
