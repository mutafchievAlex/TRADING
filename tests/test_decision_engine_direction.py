"""
Tests for DecisionEngine direction handling.
"""

import pandas as pd

from src.engines.decision_engine import DecisionEngine, DecisionResult, FailCode, Stage


def _make_minimal_df():
    return pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [102.0, 103.0],
            "low": [99.0, 100.0],
            "close": [101.0, 102.0],
            "ema50": [100.5, 101.5],
            "ema200": [99.5, 100.5],
            "atr14": [1.0, 1.0],
        }
    )


def test_short_direction_rejected_in_long_only_mode():
    df = _make_minimal_df()
    engine = DecisionEngine(config={})

    result = engine.evaluate(
        bar_index=-1,
        df=df,
        pattern=None,
        account_state={"equity": 10000.0, "open_positions": 0, "last_trade_bar": -1},
        direction="SHORT",
    )

    assert result.decision == DecisionResult.NO_TRADE
    assert result.stage == Stage.EXECUTION_GUARDS
    assert result.fail_code == FailCode.SHORT_NOT_SUPPORTED
    assert "long-only" in result.reason.lower()


def test_long_direction_still_evaluates_pipeline():
    df = _make_minimal_df()
    engine = DecisionEngine(config={})

    result = engine.evaluate(
        bar_index=-1,
        df=df,
        pattern=None,
        account_state={"equity": 10000.0, "open_positions": 0, "last_trade_bar": -1},
        direction="LONG",
    )

    assert result.decision == DecisionResult.NO_TRADE
    assert result.stage == Stage.PATTERN_DETECTION
    assert result.fail_code == FailCode.PATTERN_NOT_PRESENT
