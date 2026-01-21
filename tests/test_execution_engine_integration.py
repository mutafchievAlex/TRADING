"""Integration tests for ExecutionEngine using a mock MetaTrader5 module."""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass
from types import SimpleNamespace

import pytest


@dataclass
class FakePosition:
    ticket: int
    symbol: str
    type: int
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    profit: float
    swap: float
    comment: str
    time: int
    magic: int


@dataclass
class FakeDeal:
    ticket: int
    order: int
    time: int
    type: int
    entry: int
    volume: float
    price: float
    profit: float
    swap: float
    commission: float
    comment: str
    symbol: str
    magic: int


def _build_fake_mt5_module():
    module = types.ModuleType("MetaTrader5")
    state = SimpleNamespace(
        last_request=None,
        positions=[],
        deals=[],
        symbol_info=SimpleNamespace(visible=True, trade_allowed=True),
        symbol_selected=None,
    )

    module.TRADE_ACTION_DEAL = 1
    module.TRADE_ACTION_SLTP = 2
    module.ORDER_TYPE_BUY = 0
    module.ORDER_TYPE_SELL = 1
    module.ORDER_TIME_GTC = 0
    module.ORDER_FILLING_IOC = 1
    module.TRADE_RETCODE_DONE = 10009
    module.POSITION_TYPE_BUY = 0
    module.POSITION_TYPE_SELL = 1
    module.DEAL_TYPE_BUY = 0
    module.DEAL_TYPE_SELL = 1
    module.DEAL_ENTRY_IN = 0
    module.DEAL_ENTRY_OUT = 1

    def account_info():
        return SimpleNamespace(login=123456)

    def symbol_info(symbol):
        return state.symbol_info

    def symbol_select(symbol, enable):
        state.symbol_selected = (symbol, enable)
        return True

    def symbol_info_tick(symbol):
        return SimpleNamespace(ask=100.5, bid=100.0)

    def order_send(request):
        state.last_request = request
        return SimpleNamespace(
            retcode=module.TRADE_RETCODE_DONE,
            order=111,
            volume=request.get("volume", 0),
            price=request.get("price", 0),
            bid=100.0,
            ask=100.5,
            comment="done",
            request_id=222,
            deal=333,
        )

    def positions_get(symbol=None, ticket=None):
        if ticket is not None:
            return [pos for pos in state.positions if pos.ticket == ticket]
        if symbol is not None:
            return [pos for pos in state.positions if pos.symbol == symbol]
        return list(state.positions)

    def history_deals_get(date_from, date_to):
        return list(state.deals)

    module.account_info = account_info
    module.symbol_info = symbol_info
    module.symbol_select = symbol_select
    module.symbol_info_tick = symbol_info_tick
    module.order_send = order_send
    module.positions_get = positions_get
    module.history_deals_get = history_deals_get
    module._state = state
    return module


@pytest.fixture
def execution_engine_module(monkeypatch):
    fake_mt5 = _build_fake_mt5_module()
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake_mt5)

    import src.engines.execution_engine as execution_engine

    importlib.reload(execution_engine)
    return execution_engine, fake_mt5


def test_send_market_order_success(execution_engine_module):
    execution_engine, fake_mt5 = execution_engine_module
    engine = execution_engine.ExecutionEngine(symbol="XAUUSD", magic_number=123)

    result = engine.send_market_order(
        order_type="BUY",
        volume=0.5,
        stop_loss=99.0,
        take_profit=105.0,
        comment="Test order",
    )

    assert result is not None
    assert result["order"] == 111
    assert fake_mt5._state.last_request["type"] == fake_mt5.ORDER_TYPE_BUY
    assert fake_mt5._state.last_request["sl"] == 99.0
    assert fake_mt5._state.last_request["tp"] == 105.0


def test_send_market_order_rejects_sell(execution_engine_module):
    execution_engine, _fake_mt5 = execution_engine_module
    engine = execution_engine.ExecutionEngine(symbol="XAUUSD", magic_number=123)

    result = engine.send_market_order(order_type="SELL", volume=0.5)

    assert result is None


def test_get_open_positions_filters_magic_number(execution_engine_module):
    execution_engine, fake_mt5 = execution_engine_module
    fake_mt5._state.positions = [
        FakePosition(
            ticket=1,
            symbol="XAUUSD",
            type=fake_mt5.POSITION_TYPE_BUY,
            volume=0.5,
            price_open=100.0,
            price_current=101.0,
            sl=99.0,
            tp=105.0,
            profit=10.0,
            swap=0.0,
            comment="strategy",
            time=1,
            magic=123,
        ),
        FakePosition(
            ticket=2,
            symbol="XAUUSD",
            type=fake_mt5.POSITION_TYPE_BUY,
            volume=1.0,
            price_open=100.0,
            price_current=101.0,
            sl=99.0,
            tp=105.0,
            profit=10.0,
            swap=0.0,
            comment="other",
            time=1,
            magic=999,
        ),
    ]

    engine = execution_engine.ExecutionEngine(symbol="XAUUSD", magic_number=123)
    positions = engine.get_open_positions()

    assert len(positions) == 1
    assert positions[0]["ticket"] == 1


def test_close_position_sends_sell_order(execution_engine_module):
    execution_engine, fake_mt5 = execution_engine_module
    fake_mt5._state.positions = [
        FakePosition(
            ticket=10,
            symbol="XAUUSD",
            type=fake_mt5.POSITION_TYPE_BUY,
            volume=0.5,
            price_open=100.0,
            price_current=101.0,
            sl=99.0,
            tp=105.0,
            profit=10.0,
            swap=0.0,
            comment="strategy",
            time=1,
            magic=123,
        )
    ]

    engine = execution_engine.ExecutionEngine(symbol="XAUUSD", magic_number=123)

    assert engine.close_position(ticket=10)
    assert fake_mt5._state.last_request["type"] == fake_mt5.ORDER_TYPE_SELL


def test_modify_position_sends_sltp_request(execution_engine_module):
    execution_engine, fake_mt5 = execution_engine_module
    fake_mt5._state.positions = [
        FakePosition(
            ticket=10,
            symbol="XAUUSD",
            type=fake_mt5.POSITION_TYPE_BUY,
            volume=0.5,
            price_open=100.0,
            price_current=101.0,
            sl=99.0,
            tp=105.0,
            profit=10.0,
            swap=0.0,
            comment="strategy",
            time=1,
            magic=123,
        )
    ]

    engine = execution_engine.ExecutionEngine(symbol="XAUUSD", magic_number=123)

    assert engine.modify_position(ticket=10, stop_loss=98.5, take_profit=106.0)
    assert fake_mt5._state.last_request["action"] == fake_mt5.TRADE_ACTION_SLTP
    assert fake_mt5._state.last_request["sl"] == 98.5
    assert fake_mt5._state.last_request["tp"] == 106.0


def test_get_last_trades_filters_symbol_and_magic(execution_engine_module):
    execution_engine, fake_mt5 = execution_engine_module
    fake_mt5._state.deals = [
        FakeDeal(
            ticket=1,
            order=2,
            time=1,
            type=fake_mt5.DEAL_TYPE_BUY,
            entry=fake_mt5.DEAL_ENTRY_IN,
            volume=0.5,
            price=100.0,
            profit=10.0,
            swap=0.0,
            commission=0.0,
            comment="strategy",
            symbol="XAUUSD",
            magic=123,
        ),
        FakeDeal(
            ticket=2,
            order=3,
            time=2,
            type=fake_mt5.DEAL_TYPE_SELL,
            entry=fake_mt5.DEAL_ENTRY_OUT,
            volume=0.5,
            price=101.0,
            profit=-5.0,
            swap=0.0,
            commission=0.0,
            comment="other",
            symbol="EURUSD",
            magic=123,
        ),
    ]

    engine = execution_engine.ExecutionEngine(symbol="XAUUSD", magic_number=123)
    trades = engine.get_last_trades(count=10)

    assert len(trades) == 1
    assert trades[0]["ticket"] == 1
