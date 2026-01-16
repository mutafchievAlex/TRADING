"""
Type Definitions - TypedDict classes for data structures used throughout the system.

This module provides type-safe data structures for positions, trades, and other
key data types, enabling better IDE support, type checking, and documentation.
"""

from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class PositionData(TypedDict, total=False):
    """
    Complete position data structure.
    
    Attributes:
        ticket: Unique position identifier from MT5
        entry_price: Entry price of the position
        stop_loss: Stop loss price (may change for SL following)
        current_stop_loss: Current stop loss price (may differ from initial)
        take_profit: Original take profit price (TP3)
        tp1_price: First take profit level (1.4x RR)
        tp2_price: Second take profit level (1.9x RR)
        tp3_price: Third take profit level (2.0x RR)
        volume: Position size in lots
        direction: 1 for LONG, -1 for SHORT
        entry_time: DateTime when position was opened
        price_current: Current market price of position
        profit: Current P&L in account currency
        
        # Multi-level TP state tracking
        tp_state: Current TP state (IN_TRADE, TP1_REACHED, TP2_REACHED, CLOSED)
        tp_state_changed_at: DateTime when tp_state last changed
        bars_held_after_tp1: Number of bars held after TP1 reached
        bars_held_after_tp2: Number of bars held after TP2 reached
        
        # Trading context
        atr: ATR value at entry (for reference)
        market_regime: Market regime at entry (BULL, BEAR, RANGE)
        momentum_state: Momentum context at entry
        
        # Pattern information
        pattern_type: Type of pattern detected (Double Bottom)
        pattern_quality: Quality score of the pattern (0-10)
        
        # Risk management
        initial_risk_usd: Risk amount in USD at entry
        initial_reward_usd: Reward amount in USD at entry
        risk_reward_ratio: Risk/Reward ratio at entry
    """
    ticket: int
    entry_price: float
    stop_loss: float
    current_stop_loss: Optional[float]
    take_profit: float
    tp1_price: Optional[float]
    tp2_price: Optional[float]
    tp3_price: Optional[float]
    volume: float
    direction: int
    entry_time: Optional[str]
    price_current: Optional[float]
    profit: Optional[float]
    
    # Multi-level TP state
    tp_state: str
    tp_state_changed_at: Optional[str]
    bars_held_after_tp1: int
    bars_held_after_tp2: int
    
    # Context
    atr: Optional[float]
    market_regime: Optional[str]
    momentum_state: Optional[str]
    
    # Pattern
    pattern_type: str
    pattern_quality: Optional[float]
    
    # Risk metrics
    initial_risk_usd: Optional[float]
    initial_reward_usd: Optional[float]
    risk_reward_ratio: Optional[float]


class TradeHistory(TypedDict, total=False):
    """
    Completed trade record for history/backtesting.
    
    Attributes:
        ticket: Position identifier
        entry_price: Entry price
        exit_price: Exit price
        entry_time: Entry datetime
        exit_time: Exit datetime
        volume: Position size
        direction: 1 for LONG, -1 for SHORT
        profit: P&L in account currency
        profit_percent: P&L as percentage
        exit_reason: Reason for exit (TP1, TP2, TP3, SL, Manual, etc.)
        duration_bars: Number of bars held
        
        # Pattern information
        pattern_type: Type of pattern (Double Bottom)
        
        # Risk metrics
        risk_amount: Risk in account currency
        reward_amount: Reward in account currency
        risk_reward_ratio: Ratio of risk to reward
    """
    ticket: int
    entry_price: float
    exit_price: float
    entry_time: Optional[str]
    exit_time: Optional[str]
    volume: float
    direction: int
    profit: float
    profit_percent: float
    exit_reason: str
    duration_bars: int
    pattern_type: str
    risk_amount: float
    reward_amount: float
    risk_reward_ratio: float


class IndicatorValues(TypedDict, total=False):
    """
    Calculated indicator values for a bar.
    
    Attributes:
        ema50: Exponential Moving Average (50-period)
        ema200: Exponential Moving Average (200-period)
        atr14: Average True Range (14-period)
        close: Close price of the bar
        high: High price of the bar
        low: Low price of the bar
        open: Open price of the bar
        volume: Volume of the bar
    """
    ema50: float
    ema200: float
    atr14: float
    close: float
    high: float
    low: float
    open: float
    volume: float


class PatternData(TypedDict, total=False):
    """
    Detected pattern information.
    
    Attributes:
        pattern_detected: True if pattern detected
        pattern_type: Type of pattern (Double Bottom)
        bar_index: Bar index where pattern completes
        low_price: Low price of the pattern
        quality_score: Pattern quality (0-10)
        confirmation_bars: Number of bars until pattern confirms
        entry_price: Suggested entry price
        stop_loss: Suggested stop loss
    """
    pattern_detected: bool
    pattern_type: str
    bar_index: int
    low_price: float
    quality_score: float
    confirmation_bars: int
    entry_price: Optional[float]
    stop_loss: Optional[float]


class EntrySignal(TypedDict, total=False):
    """
    Entry signal evaluation result.
    
    Attributes:
        should_enter: True if entry conditions are met
        entry_price: Entry price if should_enter is True
        stop_loss: Stop loss price if should_enter is True
        take_profit: Take profit price if should_enter is True
        tp1_price: TP1 price for multi-level TP
        tp2_price: TP2 price for multi-level TP
        tp3_price: TP3 price for multi-level TP
        reason: Reason for entry signal or rejection
        quality_score: Quality of the entry setup (0-10)
        fail_code: Specific code for why entry was rejected
        fail_message: Human-readable failure message
    """
    should_enter: bool
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    tp1_price: Optional[float]
    tp2_price: Optional[float]
    tp3_price: Optional[float]
    reason: str
    quality_score: Optional[float]
    fail_code: Optional[str]
    fail_message: Optional[str]


class ExitSignal(TypedDict, total=False):
    """
    Exit signal evaluation result.
    
    Attributes:
        should_exit: True if exit conditions are met
        exit_reason: Reason for exit (TP1, TP2, TP3, SL, etc.)
        exit_price: Price where exit should occur
        new_tp_state: New TP state if TP level reached
        new_stop_loss: Updated stop loss if using trailing SL
    """
    should_exit: bool
    exit_reason: str
    exit_price: Optional[float]
    new_tp_state: Optional[str]
    new_stop_loss: Optional[float]


class AccountInfo(TypedDict, total=False):
    """
    MetaTrader 5 account information.
    
    Attributes:
        login: Account login number
        server: Server name
        balance: Account balance
        equity: Current equity
        free_margin: Available margin
        margin: Used margin
        margin_percent: Margin utilization percentage
        profit: Current floating profit/loss
        account_type: Type of account (DEMO or REAL)
    """
    login: int
    server: str
    balance: float
    equity: float
    free_margin: float
    margin: float
    margin_percent: float
    profit: float
    account_type: str


class MarketRegime(TypedDict, total=False):
    """
    Market regime analysis.
    
    Attributes:
        regime: Market condition (BULL, BEAR, RANGE)
        confidence: Confidence level (0.0-1.0)
        ema_distance: Distance between EMA50 and EMA200
        momentum: Current momentum
        volatility: Current volatility
    """
    regime: str
    confidence: float
    ema_distance: Optional[float]
    momentum: Optional[float]
    volatility: Optional[float]
