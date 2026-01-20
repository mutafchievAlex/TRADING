"""
Risk Engine - Calculates position sizing based on risk management rules

This module implements strict risk management:
- Fixed % risk per trade
- Position size based on distance to stop loss
- Account for commissions and spread
"""

import logging
import math
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from config import AppConfig, RiskConfig


class RiskEngine:
    """
    Manages position sizing and risk calculations.
    
    Risk formula:
    risk_amount = equity × risk_percent
    position_size = risk_amount / abs(entry_price - stop_loss)
    
    Ensures:
    - Risk remains constant per trade
    - Position size respects broker limits
    - Commissions are factored in
    """
    
    def __init__(
        self,
        risk_percent: float = 1.0,
        commission_per_lot: float = 0.0,
        config: Optional["AppConfig"] = None,
        risk_config: Optional["RiskConfig"] = None,
    ):
        """
        Initialize Risk Engine.
        
        Args:
            risk_percent: Percentage of equity to risk per trade (default: 1.0%)
            commission_per_lot: Commission per lot in account currency (default: 0.0)
            config: Optional validated app configuration
            risk_config: Optional risk config override
        """
        if config is not None:
            risk_config = config.risk
        if risk_config is not None:
            risk_percent = risk_config.risk_percent
            commission_per_lot = risk_config.commission_per_lot
        self.risk_percent = risk_percent
        self.commission_per_lot = commission_per_lot
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, 
                               equity: float,
                               entry_price: float,
                               stop_loss: float,
                               symbol_info: dict) -> Optional[float]:
        """
        Calculate position size based on risk management rules.
        
        Args:
            equity: Current account equity
            entry_price: Planned entry price
            stop_loss: Stop loss price
            symbol_info: Dict with symbol details (volume_min, volume_max, volume_step, etc.)
            
        Returns:
            Position size in lots, or None if calculation fails
        """
        try:
            # Calculate risk amount in account currency
            risk_amount = equity * (self.risk_percent / 100.0)
            
            # Calculate risk per unit (point value)
            price_risk = abs(entry_price - stop_loss)
            
            if price_risk == 0:
                self.logger.error("Invalid risk: entry price equals stop loss")
                return None
            
            # Get contract size (for XAUUSD, typically 100 oz)
            contract_size = symbol_info.get('trade_contract_size', 100.0)
            
            # Calculate position size
            # For forex/metals: position_size = risk_amount / (price_risk × contract_size)
            position_size = risk_amount / (price_risk * contract_size)
            
            # Apply broker constraints
            volume_min = symbol_info.get('volume_min', 0.01)
            volume_max = symbol_info.get('volume_max', 100.0)
            volume_step = symbol_info.get('volume_step', 0.01)
            
            # Round down to volume step
            position_size = math.floor(position_size / volume_step) * volume_step
            
            # Clamp to min/max
            position_size = max(volume_min, min(position_size, volume_max))

            # Validate risk and reduce one step if still exceeds
            if not self.validate_risk(equity, entry_price, stop_loss, position_size, symbol_info):
                position_size = max(volume_min, position_size - volume_step)

            actual_risk = (price_risk * position_size * contract_size) + (
                self.commission_per_lot * position_size * 2
            )
            actual_risk_percent = (actual_risk / equity) * 100 if equity else 0.0
            
            # Log calculation
            self.logger.info(f"Position size calculation:")
            self.logger.info(f"  Equity: ${equity:.2f}")
            self.logger.info(f"  Risk %: {self.risk_percent}%")
            self.logger.info(f"  Risk amount: ${risk_amount:.2f}")
            self.logger.info(f"  Price risk: {price_risk:.5f}")
            self.logger.info(f"  Contract size: {contract_size}")
            self.logger.info(f"  Final position size: {position_size:.2f} lots")
            self.logger.info(f"  Actual risk: {actual_risk_percent:.2f}%")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return None
    
    def calculate_potential_profit_loss(self,
                                       position_size: float,
                                       entry_price: float,
                                       exit_price: float,
                                       symbol_info: dict) -> dict:
        """
        Calculate profit/loss for a given position and exit price.
        
        Args:
            position_size: Position size in lots
            entry_price: Entry price
            exit_price: Exit price
            symbol_info: Symbol information dict
            
        Returns:
            Dict with profit/loss details
        """
        try:
            contract_size = symbol_info.get('trade_contract_size', 100.0)
            
            # Calculate P&L
            price_diff = exit_price - entry_price
            gross_pl = price_diff * position_size * contract_size
            
            # Subtract commissions
            total_commission = self.commission_per_lot * position_size * 2  # Entry + Exit
            net_pl = gross_pl - total_commission
            
            return {
                'gross_pl': gross_pl,
                'commission': total_commission,
                'net_pl': net_pl,
                'price_diff': price_diff,
                'position_size': position_size
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating P&L: {e}")
            return {
                'gross_pl': 0.0,
                'commission': 0.0,
                'net_pl': 0.0,
                'price_diff': 0.0,
                'position_size': 0.0
            }
    
    def validate_risk(self, 
                     equity: float,
                     entry_price: float,
                     stop_loss: float,
                     position_size: float,
                     symbol_info: dict) -> bool:
        """
        Validate that the position size respects risk management rules.
        
        Args:
            equity: Current equity
            entry_price: Entry price
            stop_loss: Stop loss price
            position_size: Calculated position size
            symbol_info: Symbol information
            
        Returns:
            True if risk is acceptable, False otherwise
        """
        try:
            contract_size = symbol_info.get('trade_contract_size', 100.0)
            
            # Calculate actual risk amount
            price_risk = abs(entry_price - stop_loss)
            actual_risk = price_risk * position_size * contract_size
            
            # Add commissions
            total_commission = self.commission_per_lot * position_size * 2
            actual_risk += total_commission
            
            # Calculate risk percentage
            actual_risk_percent = (actual_risk / equity) * 100
            
            # Allow small tolerance (0.1%)
            max_risk_percent = self.risk_percent + 0.1
            
            if actual_risk_percent > max_risk_percent:
                self.logger.warning(f"Risk validation failed: {actual_risk_percent:.2f}% > {max_risk_percent:.2f}%")
                return False
            
            self.logger.debug(f"Risk validated: {actual_risk_percent:.2f}% <= {max_risk_percent:.2f}%")
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating risk: {e}")
            return False
    
    def get_max_drawdown_limit(self, initial_equity: float, 
                               max_drawdown_percent: float = 10.0) -> float:
        """
        Calculate the minimum equity threshold based on max drawdown.
        
        Args:
            initial_equity: Starting equity
            max_drawdown_percent: Maximum allowed drawdown % (default: 10%)
            
        Returns:
            Minimum equity level
        """
        return initial_equity * (1 - max_drawdown_percent / 100.0)


if __name__ == "__main__":
    # Simple test
    logging.basicConfig(level=logging.DEBUG)
    
    engine = RiskEngine(risk_percent=1.0, commission_per_lot=5.0)
    
    # Mock symbol info for XAUUSD
    symbol_info = {
        'trade_contract_size': 100.0,
        'volume_min': 0.01,
        'volume_max': 100.0,
        'volume_step': 0.01
    }
    
    # Test position sizing
    equity = 10000.0
    entry = 2000.0
    stop_loss = 1980.0
    
    position_size = engine.calculate_position_size(equity, entry, stop_loss, symbol_info)
    
    if position_size:
        print(f"Position size: {position_size:.2f} lots")
        
        # Validate risk
        is_valid = engine.validate_risk(equity, entry, stop_loss, position_size, symbol_info)
        print(f"Risk valid: {is_valid}")
        
        # Calculate potential P&L
        take_profit = 2040.0
        pl_win = engine.calculate_potential_profit_loss(position_size, entry, take_profit, symbol_info)
        pl_loss = engine.calculate_potential_profit_loss(position_size, entry, stop_loss, symbol_info)
        
        print(f"Potential profit (TP): ${pl_win['net_pl']:.2f}")
        print(f"Potential loss (SL): ${pl_loss['net_pl']:.2f}")
