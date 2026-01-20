"""
Execution Engine - Sends orders to MetaTrader 5

This module handles all trade execution:
- Market orders (BUY)
- Stop loss and take profit placement
- Order status tracking
- Error handling for failed orders
"""

import MetaTrader5 as mt5
import logging
from typing import Optional, Dict, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from config import AppConfig


class ExecutionEngine:
    """
    Manages trade execution via MetaTrader 5.
    
    Responsibilities:
    - Send market orders
    - Attach stop loss and take profit
    - Handle order errors
    - Track order status
    
    Note: LONG ONLY strategy - only BUY orders
    """
    
    def __init__(
        self,
        symbol: str = "XAUUSD",
        magic_number: int = 234000,
        config: Optional["AppConfig"] = None,
    ):
        """
        Initialize Execution Engine.
        
        Args:
            symbol: Trading symbol (default: XAUUSD)
            magic_number: Unique identifier for this strategy's orders
            config: Optional validated app configuration
        """
        if config is not None:
            symbol = config.mt5.symbol
            magic_number = config.mt5.magic_number
        self.symbol = symbol
        self.magic_number = magic_number
        self.logger = logging.getLogger(__name__)
    
    def send_market_order(self,
                         order_type: str,
                         volume: float,
                         stop_loss: Optional[float] = None,
                         take_profit: Optional[float] = None,
                         deviation: int = 20,
                         comment: str = "Double Bottom Strategy") -> Optional[Dict]:
        """
        Send a market order to MT5.
        
        Args:
            order_type: "BUY" or "SELL" (but strategy is LONG ONLY)
            volume: Position size in lots
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)
            deviation: Maximum price deviation in points
            comment: Order comment
            
        Returns:
            Dict with order result, or None if failed
        """
        try:
            # Validate order type (LONG ONLY)
            if order_type != "BUY":
                self.logger.error(f"Invalid order type: {order_type}. Strategy is LONG ONLY.")
                return None
            
            # Get current price
            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                self.logger.error(f"Failed to get tick data for {self.symbol}")
                return None
            
            price = tick.ask  # For BUY orders, use ask price
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "deviation": deviation,
                "magic": self.magic_number,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,  # Good till cancelled
                "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate or cancel
            }
            
            # Add stop loss if provided
            if stop_loss is not None:
                request["sl"] = stop_loss
            
            # Add take profit if provided
            if take_profit is not None:
                request["tp"] = take_profit
            
            # Send order
            self.logger.info(f"Sending {order_type} order: {volume} lots @ {price:.5f}")
            if stop_loss:
                self.logger.info(f"  SL: {stop_loss:.5f}")
            if take_profit:
                self.logger.info(f"  TP: {take_profit:.5f}")
            
            result = mt5.order_send(request)
            
            if result is None:
                self.logger.error("order_send() returned None")
                return None
            
            # Check result
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order failed: retcode={result.retcode}, comment={result.comment}")
                return None
            
            # Success
            order_result = {
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment,
                'request_id': result.request_id,
                'retcode': result.retcode,
                'deal': result.deal,
                'timestamp': datetime.now()
            }
            
            self.logger.info(
                f"Order executed: Ticket={result.order}, Volume={result.volume}, Price={result.price:.5f}"
            )
            
            return order_result
            
        except Exception as e:
            self.logger.error(f"Error sending order: {e}")
            return None
    
    def get_open_positions(self) -> list:
        """
        Get all open positions for this symbol and magic number.
        
        Returns:
            List of position dicts
        """
        try:
            positions = mt5.positions_get(symbol=self.symbol)
            
            if positions is None:
                return []
            
            # Filter by magic number
            strategy_positions = [
                {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.POSITION_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'stop_loss': pos.sl,
                    'take_profit': pos.tp,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'comment': pos.comment,
                    'time': datetime.fromtimestamp(pos.time)
                }
                for pos in positions
                if pos.magic == self.magic_number
            ]
            
            return strategy_positions
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def close_position(self, ticket: int, close_price: Optional[float] = None) -> bool:
        """
        Close an open position by ticket number.
        
        Args:
            ticket: Position ticket number
            close_price: Optional requested close price (for logging/verification only)
            
        Returns:
            True if closed successfully, False otherwise
        """
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                self.logger.error(f"Position {ticket} not found")
                return False
            
            position = position[0]

            symbol_info = mt5.symbol_info(self.symbol)
            if symbol_info is None:
                self.logger.error("Symbol info unavailable for %s (symbol not tradeable).", self.symbol)
                return False

            if not symbol_info.visible or not symbol_info.trade_allowed:
                self.logger.warning(
                    "Symbol %s not tradeable (visible=%s trade_allowed=%s). Attempting symbol_select.",
                    self.symbol,
                    symbol_info.visible,
                    symbol_info.trade_allowed,
                )
                if not mt5.symbol_select(self.symbol, True):
                    self.logger.error("Symbol %s not tradeable after symbol_select.", self.symbol)
                    return False

            tick = mt5.symbol_info_tick(self.symbol)
            if tick is None:
                self.logger.error("Tick unavailable for %s; cannot close position.", self.symbol)
                return False

            # Determine close order type (opposite of position)
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            else:
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask

            if close_price is not None:
                self.logger.info(
                    "Close request ticket=%s requested_price=%.5f using_market_price=%.5f",
                    ticket,
                    close_price,
                    price,
                )
                if abs(close_price - price) > 1e-4:
                    self.logger.warning(
                        "Close price mismatch for ticket=%s (requested=%.5f, market=%.5f)",
                        ticket,
                        close_price,
                        price,
                    )
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": self.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": self.magic_number,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close order
            self.logger.info(f"Closing position {ticket}")
            result = mt5.order_send(request)

            if result is None:
                self.logger.error("Failed to close position: order_send returned None")
                return False

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(
                    f"Failed to close position {ticket}: retcode={result.retcode}, comment={result.comment}"
                )
                return False
            
            self.logger.info(f"Position {ticket} closed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return False
    
    def modify_position(self, ticket: int, 
                       stop_loss: Optional[float] = None,
                       take_profit: Optional[float] = None) -> bool:
        """
        Modify stop loss and/or take profit of an open position.
        
        Args:
            ticket: Position ticket number
            stop_loss: New stop loss price (optional)
            take_profit: New take profit price (optional)
            
        Returns:
            True if modified successfully, False otherwise
        """
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                self.logger.error(f"Position {ticket} not found")
                return False
            
            position = position[0]
            
            # Prepare modification request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": self.symbol,
                "position": ticket,
                "sl": stop_loss if stop_loss is not None else position.sl,
                "tp": take_profit if take_profit is not None else position.tp,
            }
            
            # Send modification
            self.logger.info(f"Modifying position {ticket}: SL={stop_loss}, TP={take_profit}")
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Failed to modify position: {result.comment if result else 'Unknown'}")
                return False
            
            self.logger.info(f"Position {ticket} modified successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error modifying position: {e}")
            return False
    
    def get_last_trades(self, count: int = 10) -> list:
        """
        Get history of last N trades.
        
        Args:
            count: Number of recent trades to retrieve
            
        Returns:
            List of trade history dicts
        """
        try:
            from datetime import datetime, timedelta
            
            # Get deals from last 30 days
            date_from = datetime.now() - timedelta(days=30)
            date_to = datetime.now()
            
            deals = mt5.history_deals_get(date_from, date_to)
            
            if deals is None:
                return []
            
            # Filter by symbol and magic number
            strategy_deals = [
                {
                    'ticket': deal.ticket,
                    'order': deal.order,
                    'time': datetime.fromtimestamp(deal.time),
                    'type': 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL',
                    'entry': 'IN' if deal.entry == mt5.DEAL_ENTRY_IN else 'OUT',
                    'volume': deal.volume,
                    'price': deal.price,
                    'profit': deal.profit,
                    'swap': deal.swap,
                    'commission': deal.commission,
                    'comment': deal.comment
                }
                for deal in deals
                if deal.symbol == self.symbol and deal.magic == self.magic_number
            ]
            
            # Sort by time descending and limit
            strategy_deals.sort(key=lambda x: x['time'], reverse=True)
            return strategy_deals[:count]
            
        except Exception as e:
            self.logger.error(f"Error getting trade history: {e}")
            return []


if __name__ == "__main__":
    # Simple test (requires active MT5 connection)
    logging.basicConfig(level=logging.DEBUG)
    
    engine = ExecutionEngine("XAUUSD", magic_number=234000)
    
    print("Execution Engine initialized")
    print("Note: Actual order testing requires MT5 connection and demo account")
    
    # Example: Get open positions
    # positions = engine.get_open_positions()
    # print(f"Open positions: {len(positions)}")
