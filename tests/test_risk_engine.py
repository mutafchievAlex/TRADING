"""
Unit tests for Risk Engine
"""

import pytest
from src.engines.risk_engine import RiskEngine


@pytest.fixture
def sample_symbol_info():
    """Sample symbol information for XAUUSD."""
    return {
        'trade_contract_size': 100.0,
        'volume_min': 0.01,
        'volume_max': 100.0,
        'volume_step': 0.01
    }


def test_risk_engine_initialization():
    """Test RiskEngine can be initialized."""
    engine = RiskEngine(risk_percent=1.0, commission_per_lot=5.0)
    assert engine is not None
    assert engine.risk_percent == 1.0
    assert engine.commission_per_lot == 5.0


def test_calculate_position_size(sample_symbol_info):
    """Test position size calculation."""
    engine = RiskEngine(risk_percent=1.0)
    
    equity = 10000.0
    entry_price = 2000.0
    stop_loss = 1980.0
    
    position_size = engine.calculate_position_size(
        equity, entry_price, stop_loss, sample_symbol_info
    )
    
    # Position size should be calculated
    assert position_size is not None
    assert position_size > 0
    
    # Should respect minimum volume
    assert position_size >= sample_symbol_info['volume_min']
    
    # Should respect maximum volume
    assert position_size <= sample_symbol_info['volume_max']


def test_calculate_position_size_respects_volume_step():
    """Ensure sizing rounds down to the configured volume step."""
    engine = RiskEngine(risk_percent=1.0)

    symbol_info = {
        'trade_contract_size': 100.0,
        'volume_min': 0.01,
        'volume_max': 10.0,
        'volume_step': 0.1,
    }

    equity = 10000.0
    entry_price = 100.0
    stop_loss = 93.0  # price risk = 7 -> size ~ 0.142 -> round to 0.1

    position_size = engine.calculate_position_size(
        equity, entry_price, stop_loss, symbol_info
    )

    assert position_size == 0.1


def test_calculate_position_size_steps_down_on_risk_validation():
    """Ensure sizing reduces when commission pushes risk over the limit."""
    engine = RiskEngine(risk_percent=1.0, commission_per_lot=50.0)

    symbol_info = {
        'trade_contract_size': 100.0,
        'volume_min': 0.01,
        'volume_max': 1.0,
        'volume_step': 0.1,
    }

    equity = 10000.0
    entry_price = 100.0
    stop_loss = 99.0  # price risk = 1 -> size = 1.0 before step-down

    position_size = engine.calculate_position_size(
        equity, entry_price, stop_loss, symbol_info
    )

    assert position_size == 0.9


def test_calculate_position_size_zero_risk(sample_symbol_info):
    """Test position size with zero risk distance."""
    engine = RiskEngine(risk_percent=1.0)
    
    equity = 10000.0
    entry_price = 2000.0
    stop_loss = 2000.0  # Same as entry - zero risk!
    
    position_size = engine.calculate_position_size(
        equity, entry_price, stop_loss, sample_symbol_info
    )
    
    # Should return None for invalid risk
    assert position_size is None


def test_calculate_potential_profit_loss(sample_symbol_info):
    """Test P&L calculation."""
    engine = RiskEngine(commission_per_lot=5.0)
    
    position_size = 0.1
    entry_price = 2000.0
    exit_price_win = 2040.0
    exit_price_loss = 1980.0
    
    # Test win scenario
    pl_win = engine.calculate_potential_profit_loss(
        position_size, entry_price, exit_price_win, sample_symbol_info
    )
    assert pl_win['gross_pl'] > 0
    assert pl_win['net_pl'] < pl_win['gross_pl']  # Commission reduces profit
    
    # Test loss scenario
    pl_loss = engine.calculate_potential_profit_loss(
        position_size, entry_price, exit_price_loss, sample_symbol_info
    )
    assert pl_loss['gross_pl'] < 0
    assert pl_loss['net_pl'] < pl_loss['gross_pl']  # Commission increases loss


def test_validate_risk(sample_symbol_info):
    """Test risk validation."""
    engine = RiskEngine(risk_percent=1.0)
    
    equity = 10000.0
    entry_price = 2000.0
    stop_loss = 1980.0
    
    # Calculate position size
    position_size = engine.calculate_position_size(
        equity, entry_price, stop_loss, sample_symbol_info
    )
    
    # Validate the calculated position size
    is_valid = engine.validate_risk(
        equity, entry_price, stop_loss, position_size, sample_symbol_info
    )
    
    assert is_valid


def test_validate_risk_rejects_over_limit(sample_symbol_info):
    """Risk validation should fail when risk exceeds tolerance."""
    engine = RiskEngine(risk_percent=1.0, commission_per_lot=10.0)

    equity = 10000.0
    entry_price = 2000.0
    stop_loss = 1990.0
    position_size = 2.0

    is_valid = engine.validate_risk(
        equity, entry_price, stop_loss, position_size, sample_symbol_info
    )

    assert not is_valid


def test_get_max_drawdown_limit():
    """Test maximum drawdown calculation."""
    engine = RiskEngine()
    
    initial_equity = 10000.0
    max_dd_percent = 10.0
    
    min_equity = engine.get_max_drawdown_limit(initial_equity, max_dd_percent)
    
    assert min_equity == 9000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
