"""
Backtest Engine - Simulates trading logic on historical data

This module runs the exact same trading logic as the live bot on historical bars,
generating a complete backtest report with metrics and trade analysis.

KEY CONSTRAINTS:
- Uses ONLY closed bars (no intrabar execution)
- Replicates live strategy logic exactly (no modifications)
- Applies realistic costs (commission, spread, slippage)
- Rolling 30-day window with 300-bar warmup
- All times in broker timezone

ARCHITECTURE:
1. Data Loading: Fetch last 30 days + warmup bars
2. Indicator Computation: EMA50, EMA200, ATR14
3. Bar-by-Bar Simulation: Apply all strategy rules
4. Cost Application: Commission on entry/exit, spread on entry
5. Metrics Calculation: 40+ performance metrics
6. Trade History: Track all trades with entry/exit details
"""

import pandas as pd
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum

# Import unified decision engine
from .decision_engine import DecisionEngine, DecisionResult, DecisionOutput, Stage, FailCode
# Import market data service
from .market_data_service import MarketDataService
from .market_regime_engine import MarketRegimeEngine


class ExitReason(Enum):
    """Reasons why a position was closed."""
    TAKE_PROFIT = "TP"
    STOP_LOSS = "SL"
    MANUAL = "MANUAL"
    RULE_EXIT = "RULE_EXIT"
    RECOVERY_EXIT = "RECOVERY_EXIT"


class TradeDirection(Enum):
    """Trade direction."""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class BacktestTrade:
    """Complete record of a single trade in backtest."""
    trade_id: int
    direction: TradeDirection
    entry_time: datetime
    entry_price: float
    entry_bar_index: int
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[ExitReason] = None
    exit_bar_index: Optional[int] = None
    quantity: float = 0.0
    risk_cash: float = 0.0
    entry_cost: float = 0.0  # Commission + spread on entry
    exit_cost: float = 0.0   # Commission on exit
    pnl_cash: float = 0.0
    pnl_percent: float = 0.0
    r_multiple: float = 0.0
    bars_held: int = 0
    sl_price: Optional[float] = None
    tp_prices: List[float] = field(default_factory=list)  # [TP1, TP2, TP3]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for export."""
        data = asdict(self)
        data['direction'] = self.direction.value
        data['exit_reason'] = self.exit_reason.value if self.exit_reason else None
        data['entry_time'] = self.entry_time.isoformat() if self.entry_time else None
        data['exit_time'] = self.exit_time.isoformat() if self.exit_time else None
        return data


class BacktestEngine:
    """
    Bar-by-bar backtest simulator matching live trading logic.
    
    Responsibilities:
    - Load historical data for last 30 days + warmup
    - Compute technical indicators
    - Simulate each bar applying trading rules
    - Track open positions and apply exit logic
    - Calculate realistic costs (commission, spread, slippage)
    - Generate comprehensive metrics and trade history
    
    NO MODIFICATIONS TO STRATEGY LOGIC - direct reuse of live components.
    """
    
    def __init__(self,
                 symbol: str = "GOLD",
                 timeframe: str = "H1",
                 rolling_days: int = 30,
                 warmup_bars: int = 300,
                 commission_percent: float = 0.02,
                 spread_points: float = 1.0,
                 slippage_points: float = 0.5,
                 config: Optional[Dict] = None):
        """
        Initialize BacktestEngine.
        
        Args:
            symbol: Trading instrument
            timeframe: Timeframe (H1, M15, etc.)
            rolling_days: Number of days to backtest (rolling window)
            warmup_bars: Bars needed for indicator warmup
            commission_percent: Commission as % of notional value
            spread_points: Fixed spread in points
            slippage_points: Fixed slippage in points
            config: Configuration dict for DecisionEngine
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.rolling_days = rolling_days
        self.warmup_bars = warmup_bars
        self.commission_percent = commission_percent
        self.spread_points = spread_points
        self.slippage_points = slippage_points
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"BacktestEngine initialized: {symbol} {timeframe}")
        self.logger.info(f"  Period: {rolling_days} days, Warmup: {warmup_bars} bars")
        self.logger.info(f"  Costs: Commission {commission_percent}%, Spread {spread_points}pt, Slippage {slippage_points}pt")
        
        # Initialize unified decision engine
        self.decision_engine = DecisionEngine(config if config else {})
        self.logger.info("Unified DecisionEngine initialized")
        # Market Regime Engine (for context in backtest)
        self.market_regime_engine = MarketRegimeEngine()
        
        # Create internal MarketDataService (used if none provided to load_historical_data)
        self.market_data_service = None
        
        # State
        self.df: Optional[pd.DataFrame] = None
        self.trades: List[BacktestTrade] = []
        self.trade_counter = 0
        self.open_positions: List[BacktestTrade] = []
        self.starting_equity = 10000.0
        self.current_equity = self.starting_equity
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.bar_tooltips: Dict[int, str] = {}  # Debugging info per bar
        self.bar_decisions: List[Dict] = []  # Per-bar decision reasons
        
        # Metrics accumulators
        self.metrics: Dict = {}
    
    def load_historical_data(self, 
                            market_data_service=None,
                            lookback_days: Optional[int] = None) -> bool:
        """
        Load historical bars for last N days + warmup bars.
        
        Args:
            market_data_service: MarketDataService instance for fetching data (optional - will create if None)
            lookback_days: Optional override for days to lookback (default: rolling_days)
            
        Returns:
            True if data loaded successfully, False otherwise
        """
        try:
            days_to_fetch = lookback_days or self.rolling_days
            bars_needed = (days_to_fetch * 24) + self.warmup_bars  # H1 timeframe
            
            self.logger.info(f"=== BACKTEST DATA REQUEST ===")
            self.logger.info(f"   Symbol: {self.symbol}")
            self.logger.info(f"   Timeframe: {self.timeframe}")
            self.logger.info(f"   Rolling days: {days_to_fetch}")
            self.logger.info(f"   Warmup bars: {self.warmup_bars}")
            self.logger.info(f"   Total bars needed: {bars_needed} ({days_to_fetch} days + {self.warmup_bars} warmup)")
            
            # Use provided market_data_service or create internal one
            if market_data_service is None:
                self.logger.info("   No MarketDataService provided, creating internal instance...")
                if self.market_data_service is None:
                    self.market_data_service = MarketDataService(symbol=self.symbol, timeframe=self.timeframe)
                    # Connection assumed to be handled externally
                    self.logger.info(f"   Created internal MarketDataService: {self.symbol}/{self.timeframe}")
                market_data_service = self.market_data_service
            
            self.logger.info(f"   MarketDataService symbol: {market_data_service.symbol}")
            self.logger.info(f"   MarketDataService timeframe: {market_data_service.timeframe}")
            
            # Fetch bars from market data service
            # Note: MarketDataService already has symbol and timeframe from init
            df = market_data_service.get_bars(count=bars_needed)
            
            if df is None:
                self.logger.error("MarketDataService returned None - no data available")
                return False
            
            if len(df) < self.warmup_bars + 2:
                self.logger.error(f"Insufficient data: got {len(df)} bars, need at least {self.warmup_bars + 2}")
                return False
            
            self.df = df.reset_index(drop=True)
            self.logger.info(f"[OK] Successfully loaded {len(self.df)} bars")
            self.logger.info(f"   Data range: {self.df['time'].min()} to {self.df['time'].max()}")
            self.logger.info(f"   Total bars: {len(self.df)}")
            self.logger.info(f"   Warmup bars: {self.warmup_bars} (bars 0-{self.warmup_bars-1})")
            self.logger.info(f"   Trading simulation will start from bar index: {self.warmup_bars}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}", exc_info=True)
            return False
    
    def run_backtest(self, 
                    strategy_engine,
                    indicator_engine,
                    risk_engine,
                    pattern_engine,
                    progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        Run bar-by-bar backtest simulation.
        
        Args:
            strategy_engine: StrategyEngine instance
            indicator_engine: IndicatorEngine instance
            risk_engine: RiskEngine instance
            pattern_engine: PatternEngine instance
            progress_callback: Optional callback function(percent, message) for progress updates
            
        Returns:
            True if backtest completed successfully
        """
        try:
            if self.df is None or len(self.df) < self.warmup_bars + 1:
                self.logger.error("No data loaded for backtest")
                return False
            
            self.logger.info(f"Starting backtest simulation on {len(self.df)} bars")
            # Precompute indicators on full dataset for UI/analysis
            try:
                self.df_with_indicators_full = indicator_engine.calculate_all_indicators(self.df)
            except Exception as e:
                self.logger.warning(f"Could not precompute full indicators: {e}")
            
            # Find warmup end index
            warmup_end_idx = self.warmup_bars
            
            self.logger.info(f"=== BACKTEST SIMULATION RANGE ===")
            self.logger.info(f"   Total bars loaded: {len(self.df)}")
            self.logger.info(f"   Warmup period: bars 0-{warmup_end_idx-1} (first {warmup_end_idx} bars)")
            self.logger.info(f"   Trading simulation: bars {warmup_end_idx}-{len(self.df)-1} ({len(self.df) - warmup_end_idx} bars)")
            backtest_start_idx = warmup_end_idx
            
            total_bars = len(self.df) - backtest_start_idx
            self.logger.info(f"Starting bar-by-bar simulation: {total_bars} bars to analyze")
            
            # Calculate delay to make backtest last approximately 10 seconds
            # If we have 1000 bars, 10000ms / 1000 = 10ms per bar
            delay_per_bar = 10.0 / total_bars if total_bars > 0 else 0  # seconds
            
            # Simulate bar by bar
            for current_bar_idx in range(backtest_start_idx, len(self.df)):
                bar_data = self.df.iloc[current_bar_idx]
                bar_time = bar_data['time']
                
                # Calculate progress percentage
                bars_processed = current_bar_idx - backtest_start_idx
                progress = int((bars_processed / total_bars) * 100) if total_bars > 0 else 0
                
                # Update progress callback if provided
                if progress_callback and bars_processed % 5 == 0:  # Update every 5 bars
                    progress_callback(progress, f"Processing bar {bars_processed}/{total_bars}")
                
                # Add small delay for visual effect (makes 10 sec total)
                if delay_per_bar > 0:
                    time.sleep(delay_per_bar)
                
                # Progress logging every 50 bars
                if bars_processed % 50 == 0:
                    self.logger.info(f"Progress: {progress}% (Bar {bars_processed}/{total_bars})")
                
                # Get data up to current bar (closed bars only)
                df_up_to_current = self.df.iloc[:current_bar_idx + 1]
                
                # Compute indicators
                df_with_indicators = indicator_engine.calculate_all_indicators(df_up_to_current)
                
                # Get current bar data (last bar in the slice)
                current_bar_data = df_with_indicators.iloc[-1]
                
                # Extract indicators from current bar
                ema50 = current_bar_data.get('ema50') if 'ema50' in current_bar_data else None
                ema200 = current_bar_data.get('ema200') if 'ema200' in current_bar_data else None
                atr14 = current_bar_data.get('atr14') if 'atr14' in current_bar_data else None
                
                # Skip bars with incomplete indicators (NaN, None, or zero ATR)
                if (pd.isna(ema50) or pd.isna(ema200) or pd.isna(atr14) or 
                    ema50 is None or ema200 is None or atr14 is None or atr14 <= 0):
                    if current_bar_idx % 50 == 0:  # Log every 50 bars to avoid spam
                        self.logger.debug(f"[Bar {current_bar_idx}] Skipping - incomplete indicators (ATR={atr14})")
                    continue
                
                # Build bar tooltip for debugging
                tooltip_lines = []
                if ema50 is not None and ema200 is not None:
                    trend = "BULLISH" if ema50 > ema200 else "BEARISH"
                    tooltip_lines.append(f"Trend: {trend} (EMA50: {ema50:.2f}, EMA200: {ema200:.2f})")
                if atr14 is not None:
                    tooltip_lines.append(f"ATR14: {atr14:.2f}")
                if len(self.open_positions) > 0:
                    tooltip_lines.append(f"🔓 Open positions: {len(self.open_positions)}")
                else:
                    tooltip_lines.append("🔒 No open positions")
                
                # Check exit conditions for open positions
                self._check_exit_conditions(current_bar_idx, bar_data, df_with_indicators)
                
                # Prepare decision tracking
                decision = {
                    'bar_index': current_bar_idx,
                    'time': str(bar_time),
                    'price_close': float(bar_data['close']),
                    'decision': 'NO_TRADE',
                    'stage': None,
                    'fail_code': None,
                    'fail_message': None,
                    # NEW: Initialize all new fields with defaults
                    'decision_timestamp': str(bar_time),
                    'decision_source': 'Backtest',
                    'decision_summary': 'NO_TRADE',
                    'planned_entry': None,
                    'planned_sl': None,
                    'planned_tp1': None,
                    'planned_tp2': None,
                    'planned_tp3': None,
                    'calculated_risk_usd': None,
                    'calculated_rr': None,
                    'position_size': None,
                    'entry_quality_score': None,
                    'quality_breakdown': None,
                    'last_closed_bar_time': str(bar_time),
                    'using_closed_bar': True,
                    'tick_noise_filter_passed': True,
                    'anti_fomo_passed': True,
                    # Regime context (computed from EMAs and close)
                    'regime': None,
                    'regime_confidence': None,
                }
                
                # Check entry conditions (only if no open positions for simplicity)
                if len(self.open_positions) == 0:
                    # Detect patterns (double bottom)
                    pattern = pattern_engine.detect_double_bottom(df_with_indicators)
                    
                    if pattern is not None:
                        self.logger.info(f"[Bar {current_bar_idx}] Double Bottom pattern detected at {bar_time}")
                        tooltip_lines.append("Pattern: Double Bottom detected")
                        
                        # ============================================================
                        # UNIFIED DECISION ENGINE - Single Source of Truth
                        # ============================================================
                        account_state = {
                            'equity': self.current_equity,
                            'open_positions': len(self.open_positions),
                            'last_trade_bar': self.trades[-1].entry_bar_index if self.trades else -9999
                        }
                        
                        # Evaluate using DecisionEngine (8-stage pipeline)
                        # Pass -1 as bar_index to use last bar in df_with_indicators slice
                        decision_output = self.decision_engine.evaluate(
                            bar_index=-1,  # Use last bar in the DataFrame slice
                            df=df_with_indicators,
                            pattern=pattern,
                            account_state=account_state,
                            direction="LONG"
                        )
                        
                        # Update decision tracking with ALL new fields
                        decision['decision'] = decision_output.decision.value
                        decision['stage'] = decision_output.stage.value if decision_output.stage else None
                        decision['fail_code'] = decision_output.fail_code.value if decision_output.fail_code else None
                        decision['fail_message'] = decision_output.reason
                        
                        # NEW: Final Decision State
                        decision['decision_timestamp'] = decision_output.decision_timestamp
                        decision['decision_source'] = 'Backtest'
                        decision['decision_summary'] = decision_output.decision_summary
                        
                        # NEW: Position Intent / Preview
                        decision['planned_entry'] = decision_output.planned_entry
                        decision['planned_sl'] = decision_output.planned_sl
                        decision['planned_tp1'] = decision_output.planned_tp1
                        decision['planned_tp2'] = decision_output.planned_tp2
                        decision['planned_tp3'] = decision_output.planned_tp3
                        decision['calculated_risk_usd'] = decision_output.calculated_risk_usd
                        decision['calculated_rr'] = decision_output.calculated_rr
                        decision['position_size'] = decision_output.position_size
                        
                        # NEW: Quality Gate / Score Breakdown
                        decision['entry_quality_score'] = decision_output.entry_quality_score
                        decision['quality_breakdown'] = decision_output.quality_breakdown
                        
                        # NEW: Bar-Close / Guard Status
                        decision['last_closed_bar_time'] = decision_output.last_closed_bar_time
                        decision['using_closed_bar'] = decision_output.using_closed_bar
                        decision['tick_noise_filter_passed'] = decision_output.tick_noise_filter_passed
                        decision['anti_fomo_passed'] = decision_output.anti_fomo_passed
                        
                        # Check if trade allowed
                        if decision_output.decision == DecisionResult.TRADE_ALLOWED:
                            self.logger.info(f"[Bar {current_bar_idx}] Entry approved by DecisionEngine!")
                            
                            # Show quality score if available
                            if decision_output.entry_quality_score:
                                self.logger.info(f"   Quality Score: {decision_output.entry_quality_score:.1f}/10")
                                if decision_output.quality_breakdown:
                                    breakdown_str = ", ".join([f"{k}={v:.1f}" for k, v in decision_output.quality_breakdown.items()])
                                    self.logger.info(f"   Breakdown: {breakdown_str}")
                            
                            # Show position preview
                            if decision_output.planned_entry and decision_output.planned_sl:
                                self.logger.info(f"   Entry: {decision_output.planned_entry:.2f}")
                                self.logger.info(f"   SL: {decision_output.planned_sl:.2f}")
                                if decision_output.planned_tp3:
                                    self.logger.info(f"   TP: {decision_output.planned_tp3:.2f}")
                                if decision_output.calculated_risk_usd:
                                    self.logger.info(f"   Risk: ${decision_output.calculated_risk_usd:.2f}")
                                if decision_output.calculated_rr:
                                    self.logger.info(f"   R:R: 1:{decision_output.calculated_rr:.1f}")
                            
                            tooltip_lines.append("Entry: APPROVED")
                            tooltip_lines.append(f"   All 8 stages passed")
                            
                            if decision_output.entry_quality_score:
                                tooltip_lines.append(f"   Quality: {decision_output.entry_quality_score:.1f}/10")
                            
                            # Calculate position sizing
                            entry_price = bar_data['close']
                            atr = decision_output.indicators.get('atr', atr14)
                            
                            # Calculate SL
                            sl_distance = atr * self.decision_engine.atr_multiplier_stop
                            sl_price = entry_price - sl_distance  # LONG
                            
                            # Calculate risk in cash
                            risk_amount = self.current_equity * (self.decision_engine.risk_percent / 100.0)
                            price_risk = abs(entry_price - sl_price)
                            
                            # Calculate quantity (simplified: risk / price_risk / contract_size)
                            contract_size = 100.0  # XAUUSD contract size
                            quantity = risk_amount / (price_risk * contract_size) if price_risk > 0 else 0.01
                            
                            # Round to 2 decimals (0.01 lot step)
                            quantity = round(quantity / 0.01) * 0.01
                            quantity = max(0.01, min(quantity, 10.0))  # Clamp to [0.01, 10.0]
                            
                            tooltip_lines.append(f"   Quantity: {quantity:.2f} lots")
                            tooltip_lines.append(f"   Risk: ${risk_amount:.2f}")
                            
                            # Create trade record
                            self._create_trade(
                                bar_idx=current_bar_idx,
                                bar_time=bar_time,
                                entry_price=entry_price,
                                sl_price=sl_price,
                                risk_cash=risk_amount,
                                quantity=quantity,
                                direction=TradeDirection.LONG
                            )
                        else:
                            # Trade rejected by DecisionEngine
                            rejection_reason = decision_output.reason or "Unknown"
                            stage = decision_output.stage.value if decision_output.stage else "UNKNOWN"
                            fail_code = decision_output.fail_code.value if decision_output.fail_code else "UNKNOWN"
                            
                            self.logger.info(f"[Bar {current_bar_idx}] Entry rejected at {stage}: {rejection_reason}")
                            tooltip_lines.append(f"Entry: REJECTED at {stage}")
                            tooltip_lines.append(f"   Code: {fail_code}")
                            tooltip_lines.append(f"   Reason: {rejection_reason}")
                            
                            # Add required vs actual if available
                            if decision_output.required and decision_output.actual:
                                tooltip_lines.append(f"   Required: {decision_output.required}")
                                tooltip_lines.append(f"   Actual: {decision_output.actual}")
                    else:
                        tooltip_lines.append("Pattern: Not detected")
                        decision['decision'] = 'PATTERN_NOT_PRESENT'
                        decision['stage'] = 'PATTERN_DETECTION'
                        decision['fail_code'] = 'PATTERN_NOT_PRESENT'
                        decision['fail_message'] = 'No Double Bottom pattern detected'

                        decision.update({
                            'decision': 'NO_TRADE',
                            'stage': '1_pattern_detection',
                            'fail_code': 'PATTERN_NOT_PRESENT',
                            'fail_message': "No valid Double Bottom pattern",
                        })

                    # Evaluate and attach regime context for this bar
                    try:
                        close_val = float(current_bar_data['close']) if 'close' in current_bar_data else None
                        if close_val is not None and ema50 is not None and ema200 is not None:
                            regime, conf = self.market_regime_engine.evaluate(close=close_val, ema50=ema50, ema200=ema200)
                            decision['regime'] = regime.value
                            decision['regime_confidence'] = conf
                    except Exception as e:
                        self.logger.debug(f"Regime evaluation skipped at bar {current_bar_idx}: {e}")

                # Store per-bar decision
                self.bar_decisions.append(decision)
                
                # Store tooltip for this bar
                if tooltip_lines:
                    self.bar_tooltips[current_bar_idx] = "\n".join(tooltip_lines)
                
                # Update equity curve
                self._update_equity_curve(bar_time)
            
            self.logger.info(f"Backtest simulation completed")
            self.logger.info(f"  Bars analyzed: {len(self.df) - warmup_end_idx}")
            self.logger.info(f"  Trades executed: {len(self.trades)}")
            self.logger.info(f"  Open positions: {len(self.open_positions)}")
            
            # Close any remaining open positions at last bar
            if self.open_positions:
                last_bar = self.df.iloc[-1]
                for trade in list(self.open_positions):
                    self._close_trade(
                        trade=trade,
                        exit_price=last_bar['close'],
                        exit_time=last_bar['time'],
                        exit_bar_idx=len(self.df) - 1,
                        exit_reason=ExitReason.MANUAL
                    )
            
            self._calculate_metrics()
            
            # Final progress update
            if progress_callback:
                progress_callback(100, "Backtest completed")
            
            self.logger.info(f"Backtest completed: {len(self.trades)} trades executed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during backtest: {e}", exc_info=True)
            return False
    
    def _create_trade(self,
                     bar_idx: int,
                     bar_time: datetime,
                     entry_price: float,
                     sl_price: float,
                     risk_cash: float,
                     quantity: float,
                     direction: TradeDirection) -> None:
        """
        Create and open a new trade.
        
        Args:
            bar_idx: Bar index where entry occurs
            bar_time: Time of entry
            entry_price: Entry price
            sl_price: Stop loss price
            risk_cash: Risk amount in cash
            quantity: Position size in lots
            direction: LONG or SHORT
        """
        self.trade_counter += 1
        
        # Entry costs: commission + spread
        notional_value = entry_price * quantity * 100  # lot size
        entry_commission = notional_value * (self.commission_percent / 100)
        entry_spread = self.spread_points * quantity * 0.1  # Rough conversion
        entry_cost = entry_commission + entry_spread
        
        trade = BacktestTrade(
            trade_id=self.trade_counter,
            direction=direction,
            entry_time=bar_time,
            entry_price=entry_price,
            entry_bar_index=bar_idx,
            quantity=quantity,
            risk_cash=risk_cash,
            entry_cost=entry_cost,
            sl_price=sl_price
        )
        
        self.open_positions.append(trade)
        self.logger.info(f"[TRADE {self.trade_counter}] OPEN {direction.value} @ {entry_price} qty={quantity:.3f} risk=${risk_cash:.2f}")
    
    def _check_exit_conditions(self,
                              bar_idx: int,
                              bar_data: pd.Series,
                              df: pd.DataFrame) -> None:
        """
        Check exit conditions for all open positions.
        
        Args:
            bar_idx: Current bar index
            bar_data: Current bar OHLC data
            df: DataFrame up to current bar
        """
        for trade in list(self.open_positions):
            close_price = bar_data['close']
            
            # Check stop loss
            if close_price <= trade.sl_price:
                self._close_trade(
                    trade=trade,
                    exit_price=trade.sl_price,
                    exit_time=bar_data['time'],
                    exit_bar_idx=bar_idx,
                    exit_reason=ExitReason.STOP_LOSS
                )
                continue
            
            # Check take profit (if TP prices set)
            if trade.tp_prices:
                for tp_idx, tp_price in enumerate(trade.tp_prices):
                    if close_price >= tp_price:
                        self._close_trade(
                            trade=trade,
                            exit_price=tp_price,
                            exit_time=bar_data['time'],
                            exit_bar_idx=bar_idx,
                            exit_reason=ExitReason.TAKE_PROFIT
                        )
                        break
    
    def _close_trade(self,
                    trade: BacktestTrade,
                    exit_price: float,
                    exit_time: datetime,
                    exit_bar_idx: int,
                    exit_reason: ExitReason) -> None:
        """
        Close an open trade.
        
        Args:
            trade: BacktestTrade to close
            exit_price: Exit price
            exit_time: Exit time
            exit_bar_idx: Exit bar index
            exit_reason: Reason for exit
        """
        trade.exit_price = exit_price
        trade.exit_time = exit_time
        trade.exit_bar_index = exit_bar_idx
        trade.exit_reason = exit_reason
        
        # Calculate PnL and costs
        if trade.direction == TradeDirection.LONG:
            pnl = (exit_price - trade.entry_price) * trade.quantity * 100
        else:  # SHORT
            pnl = (trade.entry_price - exit_price) * trade.quantity * 100
        
        # Exit commission
        notional_value = exit_price * trade.quantity * 100
        exit_commission = notional_value * (self.commission_percent / 100)
        trade.exit_cost = exit_commission
        
        total_cost = trade.entry_cost + trade.exit_cost
        trade.pnl_cash = pnl - total_cost
        trade.pnl_percent = (trade.pnl_cash / trade.risk_cash * 100) if trade.risk_cash > 0 else 0
        
        # R-multiple
        if trade.risk_cash > 0:
            trade.r_multiple = trade.pnl_cash / trade.risk_cash
        
        # Bars held
        trade.bars_held = exit_bar_idx - trade.entry_bar_index
        
        # Update equity
        self.current_equity += trade.pnl_cash
        
        # Move to completed trades
        self.open_positions.remove(trade)
        self.trades.append(trade)
        
        self.logger.info(f"[TRADE {trade.trade_id}] CLOSE {trade.exit_reason.value} @ {exit_price} "
                        f"PnL=${trade.pnl_cash:.2f} ({trade.pnl_percent:.2f}%) R={trade.r_multiple:.2f}")
    
    def _update_equity_curve(self, bar_time: datetime) -> None:
        """Update equity curve with current equity."""
        # Current equity = starting + closed trades PnL + unrealized open positions
        unrealized = sum(0 for _ in self.open_positions)  # Simplified
        current_equity = self.current_equity + unrealized
        self.equity_curve.append((bar_time, current_equity))
    
    def _calculate_metrics(self) -> None:
        """Calculate all backtest metrics."""
        try:
            if len(self.trades) == 0:
                self.logger.warning("No trades completed, metrics will be empty")
                self.metrics = {
                    'total_trades': 0,
                    'net_profit': 0,
                    'win_rate': 0,
                    'max_drawdown': 0
                }
                return
            
            # Performance metrics
            closed_pnl = [t.pnl_cash for t in self.trades]
            gross_profit = sum(p for p in closed_pnl if p > 0)
            gross_loss = abs(sum(p for p in closed_pnl if p < 0))
            net_profit = sum(closed_pnl)
            
            winning_trades = [t for t in self.trades if t.pnl_cash > 0]
            losing_trades = [t for t in self.trades if t.pnl_cash <= 0]
            
            # Basic metrics
            self.metrics = {
                'total_trades': len(self.trades),
                'long_trades': sum(1 for t in self.trades if t.direction == TradeDirection.LONG),
                'short_trades': sum(1 for t in self.trades if t.direction == TradeDirection.SHORT),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(self.trades) * 100) if self.trades else 0,
                
                'net_profit': net_profit,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'profit_factor': (gross_profit / gross_loss) if gross_loss > 0 else float('inf'),
                
                'avg_trade': net_profit / len(self.trades) if self.trades else 0,
                'best_trade': max(closed_pnl) if closed_pnl else 0,
                'worst_trade': min(closed_pnl) if closed_pnl else 0,
                
                'avg_bars_held': sum(t.bars_held for t in self.trades) / len(self.trades) if self.trades else 0,
                'max_consecutive_wins': self._calc_max_consecutive(winning_trades, self.trades),
                'max_consecutive_losses': self._calc_max_consecutive(losing_trades, self.trades),
            }
            
            # Risk metrics
            r_multiples = [t.r_multiple for t in self.trades]
            self.metrics.update({
                'avg_r_multiple': sum(r_multiples) / len(r_multiples) if r_multiples else 0,
                'expectancy_per_trade': net_profit / len(self.trades) if self.trades else 0,
                'max_drawdown': self._calc_max_drawdown(),
            })
            
            # Cost metrics
            total_commission = sum(t.entry_cost + t.exit_cost for t in self.trades)
            self.metrics.update({
                'total_costs': total_commission,
                'avg_cost_per_trade': total_commission / len(self.trades) if self.trades else 0,
            })
            
            self.logger.info(f"Metrics calculated: {self.metrics['total_trades']} trades, "
                           f"${self.metrics['net_profit']:.2f} net profit, "
                           f"{self.metrics['win_rate']:.1f}% win rate")
            
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {e}", exc_info=True)

    def _map_fail_reason(self, reason: str) -> Tuple[str, str]:
        """Map textual reason to standardized fail code and stage."""
        text = reason.lower()

        if "no valid" in text or "pattern" in text:
            return "PATTERN_QUALITY_FAIL", "2_pattern_quality"
        if "breakout" in text or "neckline" in text:
            return "NO_BREAKOUT_CONFIRMATION", "3_breakout_confirmation"
        if "trend" in text or "ema" in text:
            return "TREND_FILTER_BLOCK", "4_trend_filter"
        if "momentum" in text:
            return "MOMENTUM_TOO_WEAK", "5_momentum_filter"
        if "quality" in text:
            return "QUALITY_GATE_FAIL", "6_quality_gate"
        if "cooldown" in text:
            return "EXECUTION_GUARD_BLOCK", "7_execution_guards"
        if "risk" in text or "position" in text:
            return "RISK_MODEL_FAIL", "8_risk_validation"

        return "UNKNOWN_BLOCK", "unknown_stage"
    
    def _calc_max_consecutive(self, filtered_trades: List[BacktestTrade], all_trades: List[BacktestTrade]) -> int:
        """Calculate max consecutive wins or losses."""
        if not all_trades:
            return 0
        
        filtered_ids = {t.trade_id for t in filtered_trades}
        max_streak = 0
        current_streak = 0
        
        for trade in all_trades:
            if trade.trade_id in filtered_ids:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _calc_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve."""
        if not self.equity_curve:
            return 0
        
        equities = [eq for _, eq in self.equity_curve]
        max_equity = equities[0]
        max_dd = 0
        
        for eq in equities:
            if eq > max_equity:
                max_equity = eq
            dd = (max_equity - eq) / max_equity if max_equity > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd * 100  # Return as percentage
    
    def get_trades_dataframe(self) -> pd.DataFrame:
        """Get trades as DataFrame for export/display."""
        if not self.trades:
            return pd.DataFrame()
        
        return pd.DataFrame([t.to_dict() for t in self.trades])
    
    def get_summary(self) -> Dict:
        """Get backtest summary dict."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'period_days': self.rolling_days,
            'backtest_date': datetime.now().isoformat(),
            'metrics': self.metrics,
            'trade_count': len(self.trades),
            'starting_equity': self.starting_equity,
            'final_equity': self.current_equity,
            'bar_decisions_count': len(self.bar_decisions),
        }


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.INFO)
    
    engine = BacktestEngine(
        symbol="XAUUSD",
        timeframe="H1",
        rolling_days=30,
        warmup_bars=300,
        commission_percent=0.02,
        spread_points=1.0,
        slippage_points=0.5
    )
    
    print("BacktestEngine initialized successfully")
    print(f"Configuration: {engine.rolling_days} days, {engine.warmup_bars} bars warmup")
    print(f"Costs: {engine.commission_percent}% commission, {engine.spread_points}pt spread")
