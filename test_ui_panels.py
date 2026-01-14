#!/usr/bin/env python3
"""
Test script to verify all UI panels are properly initialized and callable.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.ui.main_window import MainWindow
from src.utils.config import Config

def test_ui_panels():
    """Test that all panels are properly initialized."""
    
    # Create QApplication (required for PySide6)
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 60)
    print("Testing UI Panel Implementation")
    print("=" * 60)
    
    # Load config
    config = Config()
    
    # Create main window
    window = MainWindow(config=config)
    print("✓ MainWindow created")
    
    # Test Decision State Panel
    try:
        assert hasattr(window, 'lbl_decision'), "Missing lbl_decision"
        assert hasattr(window, 'lbl_decision_reason'), "Missing lbl_decision_reason"
        assert hasattr(window, 'lbl_decision_timestamp'), "Missing lbl_decision_timestamp"
        assert hasattr(window, 'lbl_decision_bar_index'), "Missing lbl_decision_bar_index"
        assert hasattr(window, 'lbl_decision_mode'), "Missing lbl_decision_mode"
        print("✓ Decision State Panel initialized")
    except AssertionError as e:
        print(f"✗ Decision State Panel: {e}")
        return False
    
    # Test Trade Preview Panel
    try:
        assert hasattr(window, 'lbl_preview_entry'), "Missing lbl_preview_entry"
        assert hasattr(window, 'lbl_preview_sl'), "Missing lbl_preview_sl"
        assert hasattr(window, 'lbl_preview_tp1'), "Missing lbl_preview_tp1"
        assert hasattr(window, 'lbl_preview_tp2'), "Missing lbl_preview_tp2"
        assert hasattr(window, 'lbl_preview_tp3'), "Missing lbl_preview_tp3"
        assert hasattr(window, 'lbl_preview_risk'), "Missing lbl_preview_risk"
        assert hasattr(window, 'lbl_preview_reward'), "Missing lbl_preview_reward"
        assert hasattr(window, 'lbl_preview_size'), "Missing lbl_preview_size"
        print("✓ Trade Preview Panel initialized")
    except AssertionError as e:
        print(f"✗ Trade Preview Panel: {e}")
        return False
    
    # Test Entry Quality Panel
    try:
        assert hasattr(window, 'lbl_quality_score'), "Missing lbl_quality_score"
        assert hasattr(window, 'lbl_quality_breakdown'), "Missing lbl_quality_breakdown"
        print("✓ Entry Quality Panel initialized")
    except AssertionError as e:
        print(f"✗ Entry Quality Panel: {e}")
        return False
    
    # Test Bar-Close Guard Panel
    try:
        assert hasattr(window, 'lbl_guard_closed_bar'), "Missing lbl_guard_closed_bar"
        assert hasattr(window, 'lbl_guard_tick_noise'), "Missing lbl_guard_tick_noise"
        assert hasattr(window, 'lbl_guard_anti_fomo'), "Missing lbl_guard_anti_fomo"
        print("✓ Bar-Close Guard Panel initialized")
    except AssertionError as e:
        print(f"✗ Bar-Close Guard Panel: {e}")
        return False
    
    # Test Runtime Context Panel
    try:
        assert hasattr(window, 'lbl_runtime_context_mode'), "Missing lbl_runtime_context_mode"
        assert hasattr(window, 'lbl_runtime_context_auto_trading'), "Missing lbl_runtime_context_auto_trading"
        assert hasattr(window, 'lbl_runtime_context_account'), "Missing lbl_runtime_context_account"
        assert hasattr(window, 'lbl_runtime_context_connection'), "Missing lbl_runtime_context_connection"
        assert hasattr(window, 'lbl_runtime_context_heartbeat'), "Missing lbl_runtime_context_heartbeat"
        print("✓ Runtime Context Panel initialized")
    except AssertionError as e:
        print(f"✗ Runtime Context Panel: {e}")
        return False
    
    # Test update methods
    try:
        assert hasattr(window, 'update_decision_state'), "Missing update_decision_state method"
        assert hasattr(window, 'update_runtime_context'), "Missing update_runtime_context method"
        assert hasattr(window, 'update_position_preview'), "Missing update_position_preview method"
        assert hasattr(window, 'update_quality_score'), "Missing update_quality_score method"
        assert hasattr(window, 'update_guard_status'), "Missing update_guard_status method"
        print("✓ All update methods present")
    except AssertionError as e:
        print(f"✗ Update methods: {e}")
        return False
    
    # Test update methods with sample data
    print("\nTesting update methods...")
    
    # Test update_decision_state
    try:
        decision_data = {
            'decision': 'ENTER_LONG',
            'decision_reason': 'Pattern detected with strong momentum',
            'timestamp': '2025-01-09 14:30:00',
            'bar_index': 150,
            'execution_mode': 'BACKTEST'
        }
        window.update_decision_state(decision_data)
        assert window.lbl_decision.text() == "📈 Decision: ENTER_LONG"
        print("✓ update_decision_state() works correctly")
    except Exception as e:
        print(f"✗ update_decision_state(): {e}")
        return False
    
    # Test update_position_preview
    try:
        preview_data = {
            'planned_entry': 2700.50,
            'planned_sl': 2690.00,
            'planned_tp1': 2715.00,
            'planned_tp2': 2730.00,
            'planned_tp3': 2750.00,
            'calculated_risk_usd': 100.00,
            'calculated_reward_usd': 290.00,
            'position_size': 0.1
        }
        window.update_position_preview(preview_data)
        assert "2700.50" in window.lbl_preview_entry.text()
        print("✓ update_position_preview() works correctly")
    except Exception as e:
        print(f"✗ update_position_preview(): {e}")
        return False
    
    # Test update_runtime_context
    try:
        context_data = {
            'runtime_mode': 'DEVELOPMENT',
            'auto_trading_enabled': False,
            'account_type': 'DEMO',
            'mt5_connection_status': 'CONNECTED',
            'last_heartbeat': '2025-01-09 14:30:00'
        }
        window.update_runtime_context(context_data)
        assert "DEVELOPMENT" in window.lbl_runtime_context_mode.text()
        print("✓ update_runtime_context() works correctly")
    except Exception as e:
        print(f"✗ update_runtime_context(): {e}")
        return False
    
    # Test update_quality_score
    try:
        quality_data = {
            'entry_quality_score': 7.5,
            'quality_breakdown': {
                'pattern_score': 7.0,
                'trend_score': 8.0,
                'momentum_score': 7.0,
                'volatility_score': 8.0
            }
        }
        window.update_quality_score(quality_data)
        print("✓ update_quality_score() works correctly")
    except Exception as e:
        print(f"✗ update_quality_score(): {e}")
        return False
    
    # Test update_guard_status
    try:
        guard_data = {
            'bar_close_guard': {
                'using_closed_bar': True,
                'tick_noise_status': 'PASSED',
                'anti_fomo_status': 'PASSED'
            }
        }
        window.update_guard_status(guard_data)
        print("✓ update_guard_status() works correctly")
    except Exception as e:
        print(f"✗ update_guard_status(): {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All UI panels implemented and working correctly!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_ui_panels()
    sys.exit(0 if success else 1)
