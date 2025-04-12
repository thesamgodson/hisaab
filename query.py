"""Backward-compatible shim — re-exports everything from the queries package.

Tests monkeypatch query._conn, so this module wraps itself to intercept
setattr and propagate _conn patches to queries.common.
"""

from __future__ import annotations

import sys
import types

import queries.common as _common
from queries import *  # noqa: F401, F403
from queries import __all__ as _pkg_all
from queries.common import _conn, _fmt_rs  # noqa: F401

_ALL = [*_pkg_all, "_conn", "_fmt_rs"]


class _Module(types.ModuleType):
    """Module wrapper that propagates _conn patches to queries.common."""

    def __setattr__(self, name: str, value: object) -> None:
        if name in ("_conn", "_fmt_rs"):
            setattr(_common, name, value)
        super().__setattr__(name, value)


# Replace this module in sys.modules with the wrapper
_self = sys.modules[__name__]
_mod = _Module(__name__, __doc__)
_mod.__dict__.update(_self.__dict__)
_mod.__all__ = _ALL
_mod.__file__ = __file__
sys.modules[__name__] = _mod
