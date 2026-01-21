"""Test configuration helpers."""

from __future__ import annotations

import sys
import types


try:
    import MetaTrader5  # noqa: F401
except ModuleNotFoundError:
    mt5_stub = types.ModuleType("MetaTrader5")

    def _not_connected(*_args, **_kwargs):
        return None

    def _false(*_args, **_kwargs):
        return False

    mt5_stub.account_info = _not_connected
    mt5_stub.last_error = lambda: (1, "MetaTrader5 stub in tests")
    mt5_stub.shutdown = _false
    mt5_stub.initialize = _false
    mt5_stub.login = _false

    sys.modules["MetaTrader5"] = mt5_stub
