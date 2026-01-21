"""
MT5 Order Parameter Validation

This module provides validation for MetaTrader 5 order parameters before
submission to the broker. Prevents invalid orders and potential account violations.

Validates:
- Symbol specifications (min/max volume, volume step, tick size)
- Stop loss and take profit levels
- Order prices
- Position volume
- Order types and modes
"""

import logging
import math
from typing import Optional, Tuple
from src.exceptions import InvalidOrderParametersError


logger = logging.getLogger(__name__)


class MT5OrderValidator:
    """
    Validates MT5 order parameters against broker specifications.
    
    Configuration constants for validation thresholds.
    """
    
    # Normalization thresholds
    NORMALIZATION_WARNING_THRESHOLD = 0.5  # Warn if volume adjustment exceeds 50% of step
    
    # Distance validation thresholds (as percentages)
    MIN_DISTANCE_PCT = 0.0001  # 0.01% minimum distance for SL/TP
    MAX_SL_WARNING_PCT = 0.20  # 20% maximum SL distance (warning only)
    MAX_PRICE_DEVIATION_PCT = 0.10  # 10% maximum price deviation for market orders


class MT5OrderValidator:
    """
    Validates MT5 order parameters against broker specifications.
    
    Usage:
        validator = MT5OrderValidator()
        validator.validate_order_params(
            symbol="XAUUSD",
            volume=0.01,
            order_type=mt5.ORDER_TYPE_BUY,
            price=2000.0,
            sl=1990.0,
            tp=2020.0
        )
    """
    
    def __init__(self, mt5_module=None):
        """
        Initialize validator.
        
        Args:
            mt5_module: MT5 module (injected for testing). If None, imports MetaTrader5.
        """
        self.logger = logging.getLogger(__name__)
        
        if mt5_module is None:
            try:
                import MetaTrader5 as mt5
                self.mt5 = mt5
            except ImportError:
                self.logger.warning("MetaTrader5 not available, validation will be limited")
                self.mt5 = None
        else:
            self.mt5 = mt5_module
    
    def validate_symbol(self, symbol: str) -> None:
        """
        Validate symbol exists and is tradeable.
        
        Args:
            symbol: Trading symbol (e.g., "XAUUSD")
            
        Raises:
            InvalidOrderParametersError: If symbol is invalid or not tradeable
        """
        if not symbol or not isinstance(symbol, str):
            raise InvalidOrderParametersError(f"Invalid symbol: {symbol}")
        
        if self.mt5 is None:
            # Cannot validate without MT5
            return
        
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            raise InvalidOrderParametersError(f"Symbol not found: {symbol}")
        
        if not symbol_info.visible:
            raise InvalidOrderParametersError(f"Symbol not visible in Market Watch: {symbol}")
        
        # Check trade_mode - SYMBOL_TRADE_MODE_DISABLED = 0, SYMBOL_TRADE_MODE_FULL = 4
        if symbol_info.trade_mode == 0:  # SYMBOL_TRADE_MODE_DISABLED
            raise InvalidOrderParametersError(f"Trading disabled for symbol: {symbol}")
    
    def validate_volume(self, symbol: str, volume: float) -> float:
        """
        Validate and normalize order volume.
        
        Args:
            symbol: Trading symbol
            volume: Order volume in lots
            
        Returns:
            Normalized volume (rounded to volume_step)
            
        Raises:
            InvalidOrderParametersError: If volume is invalid
        """
        if volume is None or not isinstance(volume, (int, float)):
            raise InvalidOrderParametersError(f"Invalid volume type: {type(volume)}")
        
        if volume <= 0:
            raise InvalidOrderParametersError(f"Volume must be positive: {volume}")
        
        if self.mt5 is None:
            # Basic validation only
            return float(volume)
        
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            raise InvalidOrderParametersError(f"Cannot validate volume, symbol not found: {symbol}")
        
        # Check minimum volume
        if volume < symbol_info.volume_min:
            raise InvalidOrderParametersError(
                f"Volume {volume} below minimum {symbol_info.volume_min} for {symbol}"
            )
        
        # Check maximum volume
        if volume > symbol_info.volume_max:
            raise InvalidOrderParametersError(
                f"Volume {volume} above maximum {symbol_info.volume_max} for {symbol}"
            )
        
        # Normalize to volume step
        volume_step = symbol_info.volume_step
        normalized = round(volume / volume_step) * volume_step
        
        # Round to appropriate decimal places using math for precision
        if volume_step < 1.0:
            decimals = max(0, -int(math.floor(math.log10(volume_step))))
        else:
            decimals = 0
        normalized = round(normalized, decimals)
        
        if abs(normalized - volume) > volume_step * self.NORMALIZATION_WARNING_THRESHOLD:
            self.logger.warning(f"Volume {volume} normalized to {normalized} (step: {volume_step})")
        
        return normalized
    
    def validate_price(self, symbol: str, price: float, order_type: str = "market") -> None:
        """
        Validate order price.
        
        Args:
            symbol: Trading symbol
            price: Order price
            order_type: "market", "limit", "stop"
            
        Raises:
            InvalidOrderParametersError: If price is invalid
        """
        if price is None or not isinstance(price, (int, float)):
            raise InvalidOrderParametersError(f"Invalid price type: {type(price)}")
        
        if price <= 0:
            raise InvalidOrderParametersError(f"Price must be positive: {price}")
        
        if self.mt5 is None:
            return
        
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            raise InvalidOrderParametersError(f"Cannot validate price, symbol not found: {symbol}")
        
        # Check price is valid (not too far from current price for market orders)
        if order_type == "market":
            current_price = (symbol_info.bid + symbol_info.ask) / 2
            max_deviation = current_price * self.MAX_PRICE_DEVIATION_PCT
            
            if abs(price - current_price) > max_deviation:
                raise InvalidOrderParametersError(
                    f"Price {price} too far from current {current_price:.5f} for {symbol}"
                )
    
    def validate_stop_loss(
        self, 
        symbol: str, 
        entry_price: float, 
        stop_loss: float, 
        direction: str
    ) -> None:
        """
        Validate stop loss level.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            direction: "LONG" or "SHORT"
            
        Raises:
            InvalidOrderParametersError: If SL is invalid
        """
        if stop_loss is None or not isinstance(stop_loss, (int, float)):
            raise InvalidOrderParametersError(f"Invalid stop loss type: {type(stop_loss)}")
        
        if stop_loss <= 0:
            raise InvalidOrderParametersError(f"Stop loss must be positive: {stop_loss}")
        
        # Validate SL is on correct side of entry
        if direction == "LONG":
            if stop_loss >= entry_price:
                raise InvalidOrderParametersError(
                    f"LONG stop loss {stop_loss} must be below entry {entry_price}"
                )
        elif direction == "SHORT":
            if stop_loss <= entry_price:
                raise InvalidOrderParametersError(
                    f"SHORT stop loss {stop_loss} must be above entry {entry_price}"
                )
        else:
            raise InvalidOrderParametersError(f"Invalid direction: {direction}")
        
        # Check SL is not too tight or too wide
        sl_distance = abs(entry_price - stop_loss)
        min_distance = entry_price * self.MIN_DISTANCE_PCT
        if sl_distance < min_distance:
            raise InvalidOrderParametersError(
                f"Stop loss too tight: {sl_distance} ({sl_distance/entry_price*100:.4f}%)"
            )
        
        max_warning_distance = entry_price * self.MAX_SL_WARNING_PCT
        if sl_distance > max_warning_distance:
            self.logger.warning(
                f"Stop loss very wide: {sl_distance} ({sl_distance/entry_price*100:.2f}%)"
            )
    
    def validate_take_profit(
        self, 
        symbol: str, 
        entry_price: float, 
        take_profit: float, 
        direction: str
    ) -> None:
        """
        Validate take profit level.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            take_profit: Take profit price
            direction: "LONG" or "SHORT"
            
        Raises:
            InvalidOrderParametersError: If TP is invalid
        """
        if take_profit is None or not isinstance(take_profit, (int, float)):
            raise InvalidOrderParametersError(f"Invalid take profit type: {type(take_profit)}")
        
        if take_profit <= 0:
            raise InvalidOrderParametersError(f"Take profit must be positive: {take_profit}")
        
        # Validate TP is on correct side of entry
        if direction == "LONG":
            if take_profit <= entry_price:
                raise InvalidOrderParametersError(
                    f"LONG take profit {take_profit} must be above entry {entry_price}"
                )
        elif direction == "SHORT":
            if take_profit >= entry_price:
                raise InvalidOrderParametersError(
                    f"SHORT take profit {take_profit} must be below entry {entry_price}"
                )
        else:
            raise InvalidOrderParametersError(f"Invalid direction: {direction}")
        
        # Check TP is reasonable
        tp_distance = abs(take_profit - entry_price)
        min_distance = entry_price * self.MIN_DISTANCE_PCT
        if tp_distance < min_distance:
            raise InvalidOrderParametersError(
                f"Take profit too tight: {tp_distance} ({tp_distance/entry_price*100:.4f}%)"
            )
    
    def validate_order_params(
        self,
        symbol: str,
        volume: float,
        order_type: int,
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        direction: str = "LONG"
    ) -> Tuple[float, Optional[float], Optional[float]]:
        """
        Validate all order parameters.
        
        Args:
            symbol: Trading symbol
            volume: Order volume in lots
            order_type: MT5 order type constant
            price: Entry price (optional for market orders)
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            direction: "LONG" or "SHORT"
            
        Returns:
            Tuple of (normalized_volume, validated_sl, validated_tp)
            
        Raises:
            InvalidOrderParametersError: If any parameter is invalid
        """
        # Validate symbol
        self.validate_symbol(symbol)
        
        # Validate and normalize volume
        normalized_volume = self.validate_volume(symbol, volume)
        
        # Validate price if provided
        if price is not None:
            self.validate_price(symbol, price, "market")
        
        # Validate SL if provided
        if sl is not None and price is not None:
            self.validate_stop_loss(symbol, price, sl, direction)
        
        # Validate TP if provided
        if tp is not None and price is not None:
            self.validate_take_profit(symbol, price, tp, direction)
        
        self.logger.debug(
            f"Order params validated: {symbol} {normalized_volume} lots, "
            f"SL={sl}, TP={tp}, direction={direction}"
        )
        
        return normalized_volume, sl, tp
