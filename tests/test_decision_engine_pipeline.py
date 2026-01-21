"""
Tests for DecisionEngine pipeline stages and fail codes.
"""

import pandas as pd
import pytest

from src.engines.decision_engine import DecisionEngine, DecisionResult, FailCode, Stage


def _base_config():
    return {
        "strategy": {
            "min_bars_between": 5,
            "enable_momentum_filter": True,
            "quality_score_threshold": 8.0,
            "momentum_atr_threshold": 0.5,
            "cooldown_hours": 5,
            "pyramiding": 3,
        },
        "risk": {"risk_percent": 1.0},
    }


def _base_df(close=110.0, ema50=105.0, ema200=100.0, atr=2.0, open_price=100.0):
    return pd.DataFrame(
        {
            "open": [open_price],
            "high": [close + 1.0],
            "low": [open_price - 1.0],
            "close": [close],
            "ema50": [ema50],
            "ema200": [ema200],
            "atr14": [atr],
        }
    )


def _base_pattern():
    return {
        "left_low": {"price": 100.0, "index": 0},
        "right_low": {"price": 100.5, "index": 6},
        "neckline": {"price": 105.0},
        "quality_score": 9.0,
    }


def _base_account_state():
    return {"equity": 10000.0, "open_positions": 0, "last_trade_bar": -100}


def _base_symbol_info():
    return {
        "trade_contract_size": 100.0,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
    }


@pytest.mark.parametrize(
    "case",
    [
        {
            "name": "pattern missing",
            "pattern": None,
            "df": _base_df(),
            "account_state": _base_account_state(),
            "symbol_info": _base_symbol_info(),
            "bar_index": -1,
            "stage": Stage.PATTERN_DETECTION,
            "fail_code": FailCode.PATTERN_NOT_PRESENT,
        },
        {
            "name": "pattern quality",
            "pattern": {
                "left_low": {"price": 100.0, "index": 0},
                "right_low": {"price": 100.5, "index": 2},
                "neckline": {"price": 105.0},
                "quality_score": 9.0,
            },
            "df": _base_df(),
            "account_state": _base_account_state(),
            "symbol_info": _base_symbol_info(),
            "bar_index": -1,
            "stage": Stage.PATTERN_QUALITY,
            "fail_code": FailCode.PATTERN_QUALITY_FAIL,
        },
        {
            "name": "breakout confirmation",
            "pattern": _base_pattern(),
            "df": _base_df(close=104.0),
            "account_state": _base_account_state(),
            "symbol_info": _base_symbol_info(),
            "bar_index": -1,
            "stage": Stage.BREAKOUT_CONFIRMATION,
            "fail_code": FailCode.NO_BREAKOUT_CLOSE,
        },
        {
            "name": "trend filter",
            "pattern": _base_pattern(),
            "df": _base_df(close=110.0, ema50=120.0, ema200=100.0),
            "account_state": _base_account_state(),
            "symbol_info": _base_symbol_info(),
            "bar_index": -1,
            "stage": Stage.TREND_FILTER,
            "fail_code": FailCode.TREND_FILTER_BLOCK,
        },
        {
            "name": "momentum filter",
            "pattern": _base_pattern(),
            "df": _base_df(close=110.0, ema50=105.0, ema200=100.0, atr=5.0, open_price=109.5),
            "account_state": _base_account_state(),
            "symbol_info": _base_symbol_info(),
            "bar_index": -1,
            "stage": Stage.MOMENTUM_FILTER,
            "fail_code": FailCode.MOMENTUM_TOO_WEAK,
        },
        {
            "name": "quality gate",
            "pattern": {
                "left_low": {"price": 100.0, "index": 0},
                "right_low": {"price": 100.5, "index": 6},
                "neckline": {"price": 105.0},
                "quality_score": 5.0,
            },
            "df": _base_df(close=110.0, ema50=105.0, ema200=100.0, atr=2.0, open_price=100.0),
            "account_state": _base_account_state(),
            "symbol_info": _base_symbol_info(),
            "bar_index": -1,
            "stage": Stage.QUALITY_GATE,
            "fail_code": FailCode.QUALITY_SCORE_TOO_LOW,
        },
        {
            "name": "execution guards",
            "pattern": _base_pattern(),
            "df": _base_df(),
            "account_state": {"equity": 10000.0, "open_positions": 0, "last_trade_bar": 9},
            "symbol_info": _base_symbol_info(),
            "bar_index": 10,
            "stage": Stage.EXECUTION_GUARDS,
            "fail_code": FailCode.EXECUTION_GUARD_BLOCK,
        },
        {
            "name": "risk model",
            "pattern": _base_pattern(),
            "df": _base_df(atr=2.0),
            "account_state": _base_account_state(),
            "symbol_info": None,
            "bar_index": -1,
            "stage": Stage.RISK_MODEL,
            "fail_code": FailCode.RISK_MODEL_FAIL,
        },
    ],
)
def test_pipeline_fail_codes_and_stages(case):
    engine = DecisionEngine(config=_base_config())

    result = engine.evaluate(
        bar_index=case["bar_index"],
        df=case["df"],
        pattern=case["pattern"],
        account_state=case["account_state"],
        direction="LONG",
        symbol_info=case["symbol_info"],
    )

    assert result.decision == DecisionResult.NO_TRADE
    assert result.stage == case["stage"]
    assert result.fail_code == case["fail_code"]
