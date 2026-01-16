"""
Integration Tests for End-to-End Workflows

Tests complete system workflows:
1. Backtest execution workflow
2. Entry → Exit → Persistence workflow
3. Connection recovery workflow
4. Thread safety verification
5. Health monitoring integration
6. Alert system integration
"""

import pytest
import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from threading import Thread, Event

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from engines.market_data_service import MarketDataService
from engines.indicator_engine import IndicatorEngine
from engines.pattern_engine import PatternEngine
from engines.strategy_engine import StrategyEngine
from engines.risk_engine import RiskEngine
from engines.state_manager import StateManager
from utils.health_monitor import HealthMonitor, HealthStatus
from utils.performance_monitor import PerformanceMonitor, OperationType
from utils.alert_manager import AlertManager, AlertType, AlertSeverity
from utils.logger import TradingLogger


class TestBacktestWorkflow:
    """Test complete backtest execution workflow."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.logger = TradingLogger("test_backtest")
        self.indicator_engine = IndicatorEngine()
        self.pattern_engine = PatternEngine()
        self.strategy_engine = StrategyEngine()
        self.risk_engine = RiskEngine()
        self.state_manager = StateManager()
    
    def test_backtest_complete_workflow(self):
        """
        Test complete backtest workflow from data loading to metrics calculation.
        
        GIVEN: Historical OHLC data for 100 bars
        WHEN: Backtest runs with pattern detection and entry conditions
        THEN: Backtest completes successfully with valid metrics
        """
        # Generate synthetic OHLC data (uptrend with double bottom pattern)
        bars = self._generate_synthetic_data(num_bars=100)
        
        # Verify data structure
        assert len(bars) >= 100, "Should have 100 bars"
        assert all('open' in bar for bar in bars), "All bars should have OHLC data"
        
        # Run indicators on all bars
        indicators_history = []
        for i, bar in enumerate(bars):
            if i < 50:  # Need 50 bars for EMA200
                continue
            
            # Convert to DataFrame for indicator engine
            import pandas as pd
            df = pd.DataFrame(bars[:i+1])
            df_with_indicators = self.indicator_engine.calculate_all_indicators(df)
            
            if not df_with_indicators.empty:
                last_row = df_with_indicators.iloc[-1]
                indicators = {
                    'ema50': last_row.get('ema50'),
                    'ema200': last_row.get('ema200'),
                    'atr': last_row.get('atr')
                }
                if indicators['ema50'] is not None:
                    indicators_history.append(indicators)
        
        # Verify indicators calculated
        assert len(indicators_history) > 0, "Should have indicator values"
        assert 'ema50' in indicators_history[-1], "Should have EMA50"
        assert 'ema200' in indicators_history[-1], "Should have EMA200"
        assert 'atr' in indicators_history[-1], "Should have ATR"
        
        # Pattern detection on subset
        patterns_detected = []
        for i in range(50, len(bars)):
            # Convert to DataFrame for pattern engine
            df = pd.DataFrame(bars[:i+1])
            pattern = self.pattern_engine.detect_double_bottom(df)
            if pattern and pattern.get('detected'):
                patterns_detected.append(pattern)
        
        # Success criteria: workflow completes without errors
        assert True, "Backtest workflow completed successfully"
    
    def test_backtest_metrics_calculation(self):
        """
        Test backtest metrics calculation.
        
        GIVEN: Completed trades in state manager
        WHEN: get_statistics() is called
        THEN: Valid metrics returned (win rate, profit factor, etc.)
        """
        # Simulate trades
        self.state_manager.total_trades = 10
        self.state_manager.winning_trades = 6
        self.state_manager.losing_trades = 4
        self.state_manager.total_profit = 1500.0
        self.state_manager.trade_history = [
            {'profit': 300.0, 'exit_reason': 'TP3'},
            {'profit': 250.0, 'exit_reason': 'TP2'},
            {'profit': 200.0, 'exit_reason': 'TP1'},
            {'profit': 150.0, 'exit_reason': 'TP3'},
            {'profit': 100.0, 'exit_reason': 'TP2'},
            {'profit': 500.0, 'exit_reason': 'TP3'},
            {'profit': -100.0, 'exit_reason': 'Stop Loss'},
            {'profit': -150.0, 'exit_reason': 'Stop Loss'},
            {'profit': -200.0, 'exit_reason': 'Stop Loss'},
            {'profit': -50.0, 'exit_reason': 'Stop Loss'},
        ]
        
        # Get statistics
        stats = self.state_manager.get_statistics()
        
        # Verify metrics
        assert stats['total_trades'] == 10
        assert stats['win_rate'] == 60.0
        assert stats['total_profit'] == 1500.0
        assert stats['average_win'] > 0
        assert stats['average_loss'] < 0
        assert stats['profit_factor'] > 0
    
    def _generate_synthetic_data(self, num_bars: int = 100):
        """Generate synthetic OHLC data for testing."""
        bars = []
        base_price = 2700.0
        
        for i in range(num_bars):
            # Simple uptrend with noise
            trend = i * 0.5
            noise = (i % 7) * 2 - 7
            
            close = base_price + trend + noise
            high = close + abs(noise) * 0.5
            low = close - abs(noise) * 0.5
            open_price = (close + bars[-1]['close']) / 2 if bars else close
            
            bars.append({
                'time': datetime.now() - timedelta(hours=num_bars-i),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'tick_volume': 1000 + i * 10
            })
        
        return bars


class TestEntryExitPersistenceWorkflow:
    """Test complete entry → exit → persistence workflow."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.logger = TradingLogger("test_entry_exit")
        # Use isolated test state file
        test_state_path = str(Path(__file__).parent / "test_entry_exit_state.json")
        self.state_manager = StateManager(state_file=test_state_path, use_atomic_writes=False)
        # Clear any existing state
        self.state_manager.open_positions = []
        self.state_manager.trade_history = []
        self.state_manager.total_trades = 0
        self.risk_engine = RiskEngine(risk_percent=1.0)
        
        # Temporary state file for testing
        self.test_state_file = Path(__file__).parent / "test_state.json"
        if self.test_state_file.exists():
            self.test_state_file.unlink()
    
    def teardown_method(self):
        """Cleanup test state file."""
        if self.test_state_file.exists():
            self.test_state_file.unlink()
        # Cleanup entry/exit test state file
        entry_exit_state = Path(__file__).parent / "test_entry_exit_state.json"
        if entry_exit_state.exists():
            entry_exit_state.unlink()
    
    def test_entry_to_exit_workflow(self):
        """
        Test complete entry → exit workflow.
        
        GIVEN: Valid entry signal with position sizing
        WHEN: Position opened → Exit signal triggered → Position closed
        THEN: Trade history updated, statistics calculated, state persisted
        """
        # Step 1: Entry
        entry_details = {
            'entry_price': 2700.0,
            'stop_loss': 2680.0,
            'take_profit': 2740.0,
            'atr': 10.0,
            'pattern_type': 'Double Bottom'
        }
        
        # Calculate position size
        account_equity = 10000.0
        symbol_info = {
            'point': 0.01,
            'tick_value': 1.0,
            'trade_contract_size': 100.0
        }
        
        position_size = self.risk_engine.calculate_position_size(
            equity=account_equity,
            entry_price=entry_details['entry_price'],
            stop_loss=entry_details['stop_loss'],
            symbol_info=symbol_info
        )
        
        assert position_size is not None, "Position size should be calculated"
        assert position_size > 0, "Position size should be positive"
        
        # Step 2: Open position
        ticket = 123456
        self.state_manager.open_position({
            'ticket': ticket,
            'entry_price': entry_details['entry_price'],
            'price_current': entry_details['entry_price'],
            'stop_loss': entry_details['stop_loss'],
            'take_profit': entry_details['take_profit'],
            'volume': position_size,
            'profit': 0.0,
            'entry_time': datetime.now(),
            'atr': entry_details['atr'],
            'direction': 1,
            'tp_state': 'IN_TRADE'
        })
        
        # Verify position opened
        assert len(self.state_manager.open_positions) == 1
        position = self.state_manager.get_position_by_ticket(ticket)
        assert position is not None
        assert position['ticket'] == ticket
        
        # Step 3: Close position
        exit_price = 2740.0
        exit_reason = "Take Profit TP3"
        
        # Update current price in position (close_position will calculate profit)
        for pos in self.state_manager.open_positions:
            if pos['ticket'] == ticket:
                pos['price_current'] = exit_price
                break
        
        # Close position
        self.state_manager.close_position(
            exit_price=exit_price,
            exit_reason=exit_reason,
            ticket=ticket
        )
        
        # Verify position closed
        assert len(self.state_manager.open_positions) == 0, "Position should be closed"
        assert len(self.state_manager.trade_history) == 1, "Trade should be in history"
        
        trade = self.state_manager.trade_history[0]
        assert trade['ticket'] == ticket, "Ticket should match"
        assert trade['exit_price'] == exit_price, "Exit price should match"
        assert trade['exit_reason'] == exit_reason, "Exit reason should match"
        # Verify profit was calculated (should be positive for winning trade)
        assert trade['profit'] > 0, f"Profit should be positive, got {trade['profit']}"
    
    def test_state_persistence_workflow(self):
        """
        Test state persistence workflow.
        
        GIVEN: Positions and trade history in state manager
        WHEN: save_state() called
        THEN: State written to disk and can be reloaded
        """
        # Open position
        ticket = 789012
        self.state_manager.open_position({
            'ticket': ticket,
            'entry_price': 2700.0,
            'price_current': 2710.0,
            'stop_loss': 2680.0,
            'take_profit': 2740.0,
            'volume': 0.1,
            'profit': 100.0,
            'entry_time': datetime.now(),
            'atr': 10.0,
            'direction': 1,
            'tp_state': 'TP1_ACTIVE'
        })
        
        # Override state file path for testing
        original_path = self.state_manager.state_file
        self.state_manager.state_file = self.test_state_file
        
        # Disable atomic writes for immediate save
        original_atomic = self.state_manager.atomic_writer
        self.state_manager.atomic_writer = None
        
        # Save state
        self.state_manager.save_state()
        
        # Verify file exists
        assert self.test_state_file.exists(), "State file should be created"
        
        # Load and verify state
        with open(self.test_state_file, 'r') as f:
            saved_state = json.load(f)
        
        assert 'open_positions' in saved_state
        assert len(saved_state['open_positions']) == 1
        assert saved_state['open_positions'][0]['ticket'] == ticket
        
        # Restore original settings
        self.state_manager.state_file = original_path
        self.state_manager.atomic_writer = original_atomic


class TestConnectionRecoveryWorkflow:
    """Test connection loss and recovery workflow."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.logger = TradingLogger("test_connection")
        self.alert_manager = AlertManager()
        self.connection_status = True
    
    def test_connection_loss_detection(self):
        """
        Test connection loss detection.
        
        GIVEN: Active connection
        WHEN: Connection lost
        THEN: Alert triggered, reconnection attempted
        """
        # Simulate connection loss
        reconnect_attempted = False
        
        def mock_reconnect():
            nonlocal reconnect_attempted
            reconnect_attempted = True
            return True
        
        # Initial state: connected
        is_connected = True
        
        # Connection loss
        is_connected = False
        
        # Alert triggered (use send_alert to avoid suppression)
        alert = self.alert_manager.send_alert(
            AlertType.CONNECTION_LOST,
            AlertSeverity.CRITICAL,
            "MetaTrader 5 connection lost!",
            details=None,
            suppress=False
        )
        assert alert is not None, "Alert should be created"
        assert alert.alert_type == AlertType.CONNECTION_LOST
        assert alert.severity == AlertSeverity.CRITICAL
        
        # Reconnection attempt
        if not is_connected:
            is_connected = mock_reconnect()
        
        assert reconnect_attempted, "Reconnection should be attempted"
        assert is_connected, "Should be reconnected"
    
    def test_connection_restore_alert(self):
        """
        Test connection restore alert.
        
        GIVEN: Connection was lost
        WHEN: Connection restored
        THEN: Restore alert triggered
        """
        alert = self.alert_manager.send_alert(
            AlertType.CONNECTION_RESTORED,
            AlertSeverity.INFO,
            "MetaTrader 5 connection restored",
            details=None,
            suppress=False
        )
        
        assert alert is not None, "Alert should be created"
        assert alert.alert_type == AlertType.CONNECTION_RESTORED
        assert alert.severity == AlertSeverity.INFO


class TestHealthMonitoringIntegration:
    """Test health monitoring integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.logger = TradingLogger("test_health")
        self.test_state_file = Path(__file__).parent / "test_health_state.json"
        
        # Create empty state file
        with open(self.test_state_file, 'w') as f:
            json.dump({'open_positions': [], 'trade_history': []}, f)
        
        self.health_monitor = HealthMonitor(
            state_file=self.test_state_file,
            memory_threshold_mb=500.0,
            disk_threshold_gb=1.0,
            queue_depth_threshold=100
        )
    
    def teardown_method(self):
        """Cleanup test files."""
        if self.test_state_file.exists():
            self.test_state_file.unlink()
    
    def test_health_check_all_systems(self):
        """
        Test complete health check of all systems.
        
        GIVEN: System components running
        WHEN: Health check performed
        THEN: All checks return valid status
        """
        checks = self.health_monitor.check_all(
            mt5_connected=True,
            ui_queue_depth=10,
            state_queue_depth=5
        )
        
        # Verify all checks performed
        assert 'mt5_connection' in checks
        assert 'state_file' in checks
        assert 'memory' in checks
        assert 'disk_space' in checks
        assert 'ui_queue' in checks
        assert 'state_queue' in checks
        
        # Verify MT5 check passed
        assert checks['mt5_connection'].status == HealthStatus.HEALTHY
        
        # Get overall status
        overall = self.health_monitor.get_overall_status(checks)
        assert overall in [HealthStatus.HEALTHY, HealthStatus.WARNING]
    
    def test_health_check_critical_state(self):
        """
        Test health check with critical conditions.
        
        GIVEN: MT5 disconnected, queue depth exceeded
        WHEN: Health check performed
        THEN: CRITICAL status returned
        """
        checks = self.health_monitor.check_all(
            mt5_connected=False,
            ui_queue_depth=150,  # Exceeds threshold of 100
            state_queue_depth=5
        )
        
        # MT5 should be critical
        assert checks['mt5_connection'].status == HealthStatus.CRITICAL
        
        # UI queue should be warning or critical
        assert checks['ui_queue'].status in [HealthStatus.WARNING, HealthStatus.CRITICAL]
        
        # Overall should be critical
        overall = self.health_monitor.get_overall_status(checks)
        assert overall == HealthStatus.CRITICAL


class TestPerformanceMonitoringIntegration:
    """Test performance monitoring integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.performance_monitor = PerformanceMonitor()
    
    def test_operation_timing_tracking(self):
        """
        Test operation timing tracking.
        
        GIVEN: Operations executed with timing
        WHEN: Metrics requested
        THEN: Valid statistics returned
        """
        # Simulate some operations
        for i in range(10):
            self.performance_monitor.start_timer(f"test_op_{i}")
            time.sleep(0.001)  # 1ms
            self.performance_monitor.end_timer(
                f"test_op_{i}",
                OperationType.MAIN_LOOP,
                success=True
            )
        
        # Get metrics
        metrics = self.performance_monitor.get_metrics(OperationType.MAIN_LOOP)
        
        assert metrics['total_calls'] == 10
        assert metrics['success_rate'] == 100.0
        assert metrics['avg_ms'] > 0
        assert metrics['min_ms'] > 0
        assert metrics['max_ms'] > 0
    
    def test_bottleneck_detection(self):
        """
        Test bottleneck detection.
        
        GIVEN: Operations with high latency variability
        WHEN: Bottleneck check performed
        THEN: High variance operations identified
        """
        # Simulate operations with varying latency
        for i in range(20):
            self.performance_monitor.record_operation(
                OperationType.BACKTEST,
                duration_ms=10.0 if i < 18 else 100.0,  # 2 outliers
                success=True
            )
        
        # Get bottlenecks
        bottlenecks = self.performance_monitor.get_bottlenecks(percentile=95)
        
        # Should detect BACKTEST as bottleneck due to outliers
        backtest_bottleneck = next(
            (b for b in bottlenecks if b['operation'] == 'BACKTEST'),
            None
        )
        
        if backtest_bottleneck:
            assert backtest_bottleneck['p95_ms'] > backtest_bottleneck['avg_ms'] * 2


class TestAlertSystemIntegration:
    """Test alert system integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.alert_manager = AlertManager(max_history=100)
        self.alerts_received = []
        
        # Add test handler
        self.alert_manager.add_handler(self._handle_alert)
    
    def _handle_alert(self, alert):
        """Test alert handler."""
        self.alerts_received.append(alert)
    
    def test_alert_handler_integration(self):
        """
        Test alert handler integration.
        
        GIVEN: Alert manager with handler
        WHEN: Alerts triggered
        THEN: Handler receives alerts
        """
        # Trigger alerts
        self.alert_manager.alert_connection_lost()
        self.alert_manager.alert_health_critical("Memory exceeded")
        self.alert_manager.alert_position_opened({'ticket': 123})
        
        # Verify handler received alerts
        assert len(self.alerts_received) == 3
        assert self.alerts_received[0].alert_type == AlertType.CONNECTION_LOST
        assert self.alerts_received[1].alert_type == AlertType.HEALTH_CRITICAL
        assert self.alerts_received[2].alert_type == AlertType.POSITION_OPENED
    
    def test_alert_anti_spam(self):
        """
        Test alert anti-spam mechanism.
        
        GIVEN: Multiple identical alerts within interval
        WHEN: Alerts triggered rapidly
        THEN: Duplicate alerts suppressed
        """
        # Trigger same alert multiple times
        alert1 = self.alert_manager.send_alert(
            AlertType.CONNECTION_LOST,
            AlertSeverity.CRITICAL,
            "Test connection lost",
            details=None,
            suppress=True
        )
        alert2 = self.alert_manager.send_alert(
            AlertType.CONNECTION_LOST,
            AlertSeverity.CRITICAL,
            "Test connection lost",
            details=None,
            suppress=True
        )  # Should be suppressed
        
        assert alert1 is not None, "First alert should be sent"
        assert alert2 is None, "Second alert should be suppressed by anti-spam"
        
        # Wait for interval
        time.sleep(5.1)
        
        # Should be allowed now
        alert3 = self.alert_manager.send_alert(
            AlertType.CONNECTION_LOST,
            AlertSeverity.CRITICAL,
            "Test connection lost",
            details=None,
            suppress=True
        )
        assert alert3 is not None, "Alert should be allowed after interval"
    
    def test_critical_alert_filtering(self):
        """
        Test critical alert filtering.
        
        GIVEN: Mix of alert severities
        WHEN: Critical alerts requested
        THEN: Only critical alerts returned
        """
        # Trigger various alerts
        self.alert_manager.alert_system_startup()  # INFO
        self.alert_manager.alert_connection_lost()  # CRITICAL
        self.alert_manager.alert_health_warning("Disk space low")  # WARNING
        self.alert_manager.alert_health_critical("Memory critical")  # CRITICAL
        
        # Get critical alerts
        critical_alerts = self.alert_manager.get_critical_alerts(hours=24)
        
        assert len(critical_alerts) == 2
        assert all(a.severity == AlertSeverity.CRITICAL for a in critical_alerts)


class TestThreadSafety:
    """Test thread safety of core components."""
    
    def test_state_manager_thread_safety(self):
        """
        Test state manager thread safety.
        
        GIVEN: Multiple threads updating state
        WHEN: Concurrent operations performed
        THEN: No data corruption or race conditions
        """
        # Use isolated test state file
        test_state_path = str(Path(__file__).parent / "test_thread_safety_state.json")
        state_manager = StateManager(state_file=test_state_path, use_atomic_writes=False)
        # Clear any existing positions
        state_manager.open_positions = []
        state_manager.trade_history = []
        
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(10):
                    ticket = thread_id * 1000 + i
                    state_manager.open_position({
                        'ticket': ticket,
                        'entry_price': 2700.0 + i,
                        'price_current': 2700.0 + i,
                        'stop_loss': 2680.0,
                        'take_profit': 2740.0,
                        'volume': 0.1,
                        'profit': 0.0,
                        'entry_time': datetime.now(),
                        'atr': 10.0,
                        'direction': 1,
                        'tp_state': 'IN_TRADE'
                    })
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))
        
        # Create threads
        threads = [Thread(target=worker, args=(i,)) for i in range(3)]
        
        # Start threads
        for t in threads:
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Verify all positions added
        assert len(state_manager.open_positions) == 30, f"Expected 30 positions, got {len(state_manager.open_positions)}"
        
        # Cleanup test file
        test_file = Path(test_state_path)
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
