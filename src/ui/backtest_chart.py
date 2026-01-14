"""
Bar-by-Bar Backtest Chart Widget

Visualizes backtest execution with:
- Candlestick price chart
- Equity curve overlay
- Trade entry/exit markers
- Risk/profit boxes
- Playback controls (step forward, auto play)
- Bar-by-bar debugging tooltips
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QSlider, QComboBox, QCheckBox, QGroupBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

try:
    from PySide6.QtCharts import (
        QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis, QScatterSeries
    )
    HAS_CHART = True
except ImportError:
    HAS_CHART = False
    QChart = None
    QChartView = None
    QLineSeries = None
    QValueAxis = None
    QDateTimeAxis = None
    QScatterSeries = None

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging


class CandlestickItem:
    """Single candlestick for custom drawing."""
    def __init__(self, time, open_price, high, low, close):
        self.time = time
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.is_bullish = close >= open_price


class TradeMarker:
    """Trade entry/exit marker."""
    def __init__(self, time, price, marker_type, color, label):
        self.time = time
        self.price = price
        self.marker_type = marker_type  # 'entry', 'exit', 'sl', 'tp'
        self.color = color
        self.label = label


class BacktestChartWidget(QWidget):
    """
    Interactive bar-by-bar backtest chart with playback controls.
    
    Features:
    - Candlestick price chart with custom drawing
    - Equity curve overlay on secondary axis
    - Trade markers (entry/exit/sl/tp)
    - Trade boxes (risk/profit rectangles)
    - Playback controls (step forward, play/pause, speed control)
    - Hover tooltips with debugging info
    """
    
    # Signals
    bar_changed = Signal(int)  # Emitted when current bar changes
    playback_finished = Signal()  # Emitted when playback reaches end
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Data
        self.price_bars = None  # DataFrame with OHLC data
        self.equity_curve = []  # List of (bar_idx, equity_value)
        self.trade_markers = []  # List of TradeMarker objects
        self.trade_boxes = []  # List of (entry_bar, exit_bar, entry_price, exit_price, is_win)
        self.bar_tooltips = {}  # Dict[bar_idx] -> tooltip_text
        
        # Playback state
        self.current_bar_idx = 0
        self.max_bar_idx = 0
        self.is_playing = False
        self.playback_speed = 1.0  # 1x, 2x, 5x, 10x
        self.data_loaded = False  # Track if backtest data is loaded
        self.run_backtest_callback = None  # Callback to run backtest
        
        # Timer for auto-play
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.step_forward)
        
        # Chart components (will be created if QtCharts available)
        self.chart_view = None
        self.chart = None
        self.price_series = None
        self.equity_series = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI layout."""
        layout = QVBoxLayout()
        
        # Playback controls
        controls_group = QGroupBox("Playback Controls")
        controls_layout = QHBoxLayout()
        
        self.play_pause_btn = QPushButton("Run Backtest")
        self.play_pause_btn.setMinimumWidth(150)
        self.play_pause_btn.clicked.connect(self.on_play_clicked)
        controls_layout.addWidget(self.play_pause_btn)
        
        self.step_btn = QPushButton("Step")
        self.step_btn.setMinimumWidth(80)
        self.step_btn.clicked.connect(self.step_forward)
        controls_layout.addWidget(self.step_btn)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setMinimumWidth(80)
        self.reset_btn.clicked.connect(self.reset_playback)
        controls_layout.addWidget(self.reset_btn)
        
        controls_layout.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1x", "2x", "5x", "10x"])
        self.speed_combo.currentTextChanged.connect(self.on_speed_changed)
        controls_layout.addWidget(self.speed_combo)
        
        controls_layout.addStretch()
        
        self.bar_label = QLabel("Bar: 0 / 0")
        controls_layout.addWidget(self.bar_label)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Chart view
        if HAS_CHART:
            self.chart_view = BacktestChartView()
            self.chart_view.setMinimumHeight(400)
            layout.addWidget(self.chart_view)
        else:
            fallback = QLabel("QtCharts not available. Install PySide6-QtCharts for visualization.")
            fallback.setStyleSheet("padding: 20px; background-color: #FFF3CD; border: 1px solid #FFE082;")
            layout.addWidget(fallback)
        
        # Bar info panel (shows debugging info for current bar)
        self.bar_info_label = QLabel("Click Run Backtest to start")
        self.bar_info_label.setWordWrap(True)
        self.bar_info_label.setStyleSheet("""
            QLabel {
                background-color: #E8F5E9;
                padding: 10px;
                border: 1px solid #4CAF50;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
                color: #000000;
            }
        """)
        layout.addWidget(self.bar_info_label)
        
        self.setLayout(layout)
    
    def load_data(self, 
                  price_bars: pd.DataFrame,
                  equity_curve: List[Tuple[int, float]],
                  trades: List[Dict],
                  bar_tooltips: Optional[Dict[int, str]] = None):
        """
        Load backtest data into chart.
        
        Args:
            price_bars: DataFrame with columns [time, open, high, low, close]
            equity_curve: List of (bar_idx, equity_value) tuples
            trades: List of trade dicts with entry/exit info
            bar_tooltips: Optional dict of bar_idx -> tooltip text for debugging
        """
        try:
            self.logger.info(f"Loading chart data: {len(price_bars)} bars, {len(trades)} trades")
            
            self.price_bars = price_bars.copy()
            self.equity_curve = equity_curve
            self.bar_tooltips = bar_tooltips or {}
            
            self.max_bar_idx = len(price_bars) - 1
            self.current_bar_idx = 0
            
            # Convert trades to markers and boxes
            self._process_trades(trades)
            
            # Build chart if QtCharts available
            if HAS_CHART and self.chart_view:
                self._build_chart()
            
            # Update UI
            self._update_bar_label()
            self._update_bar_info()
            
            # Mark data as loaded and update button
            self.data_loaded = True
            self.play_pause_btn.setText("Play")
            
            self.logger.info("Chart data loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Error loading chart data: {e}", exc_info=True)
    
    def _process_trades(self, trades: List[Dict]):
        """Convert trade records to visual markers and boxes."""
        self.trade_markers = []
        self.trade_boxes = []
        
        for trade in trades:
            # Entry marker
            entry_marker = TradeMarker(
                time=trade.get('entry_time'),
                price=trade.get('entry_price'),
                marker_type='entry',
                color=QColor("#00E676"),
                label="Entry"
            )
            self.trade_markers.append(entry_marker)
            
            # Exit marker
            exit_reason = trade.get('exit_reason', '')
            if 'SL' in exit_reason or 'STOP' in exit_reason:
                marker_type = 'sl'
                color = QColor("#FF1744")
                label = "SL"
            elif 'TP' in exit_reason or 'TAKE' in exit_reason:
                marker_type = 'tp'
                color = QColor("#FFD600")
                label = "TP"
            else:
                marker_type = 'exit'
                color = QColor("#FF5252")
                label = "Exit"
            
            exit_marker = TradeMarker(
                time=trade.get('exit_time'),
                price=trade.get('exit_price'),
                marker_type=marker_type,
                color=color,
                label=label
            )
            self.trade_markers.append(exit_marker)
            
            # Trade box (for profit/loss visualization)
            is_win = trade.get('pnl', 0) > 0
            trade_box = {
                'entry_bar': trade.get('entry_bar_idx', 0),
                'exit_bar': trade.get('exit_bar_idx', 0),
                'entry_price': trade.get('entry_price'),
                'exit_price': trade.get('exit_price'),
                'sl_price': trade.get('sl_price'),
                'tp_price': trade.get('tp_price'),
                'is_win': is_win
            }
            self.trade_boxes.append(trade_box)
    
    def _build_chart(self):
        """Build QtCharts chart with price and equity data."""
        if not HAS_CHART:
            return
        
        # Create chart
        self.chart = QChart()
        self.chart.setTitle("Bar-by-Bar Backtest Replay")
        self.chart.setAnimationOptions(QChart.NoAnimation)
        
        # Price series (simplified as line for now, custom candlesticks later)
        self.price_series = QLineSeries()
        self.price_series.setName("Close Price")
        
        for idx, row in self.price_bars.iterrows():
            timestamp = pd.to_datetime(row['time']).timestamp() * 1000  # milliseconds
            self.price_series.append(timestamp, row['close'])
        
        self.chart.addSeries(self.price_series)
        
        # Equity series (secondary axis)
        self.equity_series = QLineSeries()
        self.equity_series.setName("Equity")
        self.equity_series.setColor(QColor("#00C853"))
        
        for bar_idx, equity_value in self.equity_curve:
            if bar_idx < len(self.price_bars):
                timestamp = pd.to_datetime(self.price_bars.iloc[bar_idx]['time']).timestamp() * 1000
                self.equity_series.append(timestamp, equity_value)
        
        self.chart.addSeries(self.equity_series)
        
        # Create axes
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MMM dd HH:mm")
        axis_x.setTitleText("Time")
        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.price_series.attachAxis(axis_x)
        self.equity_series.attachAxis(axis_x)
        
        axis_y_price = QValueAxis()
        axis_y_price.setTitleText("Price")
        self.chart.addAxis(axis_y_price, Qt.AlignLeft)
        self.price_series.attachAxis(axis_y_price)
        
        axis_y_equity = QValueAxis()
        axis_y_equity.setTitleText("Equity ($)")
        self.chart.addAxis(axis_y_equity, Qt.AlignRight)
        self.equity_series.attachAxis(axis_y_equity)
        
        # Add trade markers as scatter series
        self._add_trade_markers_to_chart()
        
        # Set chart to view
        self.chart_view.setChart(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
    
    def _add_trade_markers_to_chart(self):
        """Add trade entry/exit markers as scatter series."""
        if not HAS_CHART:
            return
        
        # Entry markers
        entry_series = QScatterSeries()
        entry_series.setName("Entries")
        entry_series.setColor(QColor("#00E676"))
        entry_series.setMarkerSize(12)
        
        # Exit markers
        exit_series = QScatterSeries()
        exit_series.setName("Exits")
        exit_series.setColor(QColor("#FF5252"))
        exit_series.setMarkerSize(12)
        
        for marker in self.trade_markers:
            timestamp = pd.to_datetime(marker.time).timestamp() * 1000
            
            if marker.marker_type == 'entry':
                entry_series.append(timestamp, marker.price)
            else:
                exit_series.append(timestamp, marker.price)
        
        if entry_series.count() > 0:
            self.chart.addSeries(entry_series)
            entry_series.attachAxis(self.chart.axes(Qt.Horizontal)[0])
            entry_series.attachAxis(self.chart.axes(Qt.Vertical)[0])
        
        if exit_series.count() > 0:
            self.chart.addSeries(exit_series)
            exit_series.attachAxis(self.chart.axes(Qt.Horizontal)[0])
            exit_series.attachAxis(self.chart.axes(Qt.Vertical)[0])
    
    def on_play_clicked(self):
        """Handle play button click - run backtest if not loaded, otherwise toggle playback."""
        if not self.data_loaded:
            # Run backtest first
            if self.run_backtest_callback:
                self.logger.info("Running backtest...")
                self.run_backtest_callback()
            else:
                self.logger.error("Backtest callback not connected")
                self.bar_info_label.setText("Error: Backtest not available")
        else:
            # Data is loaded, toggle playback
            self.toggle_play_pause()
    
    def toggle_play_pause(self):
        """Toggle playback play/pause."""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        """Start automatic playback."""
        if self.current_bar_idx >= self.max_bar_idx:
            self.reset_playback()
        
        self.is_playing = True
        self.play_pause_btn.setText("Pause")
        
        # Calculate interval based on speed (base 500ms at 1x)
        interval_ms = int(500 / self.playback_speed)
        self.playback_timer.start(interval_ms)
        
        self.logger.info(f"Playback started at {self.playback_speed}x speed")
    
    def pause_playback(self):
        """Pause automatic playback."""
        self.is_playing = False
        self.play_pause_btn.setText("Play")
        self.playback_timer.stop()
        
        self.logger.info("Playback paused")
    
    def step_forward(self):
        """Advance to next bar."""
        if self.current_bar_idx < self.max_bar_idx:
            self.current_bar_idx += 1
            self._update_bar_label()
            self._update_bar_info()
            self._highlight_current_bar()
            
            self.bar_changed.emit(self.current_bar_idx)
        else:
            # Reached end
            if self.is_playing:
                self.pause_playback()
                self.playback_finished.emit()
                self.logger.info("Playback finished")
    
    def reset_playback(self):
        """Reset playback to beginning."""
        self.current_bar_idx = 0
        self._update_bar_label()
        self._update_bar_info()
        self._highlight_current_bar()
        
        self.logger.info("Playback reset")
    
    def on_speed_changed(self, speed_text: str):
        """Handle speed combo box change."""
        speed_map = {"1x": 1.0, "2x": 2.0, "5x": 5.0, "10x": 10.0}
        self.playback_speed = speed_map.get(speed_text, 1.0)
        
        # Update timer if playing
        if self.is_playing:
            interval_ms = int(500 / self.playback_speed)
            self.playback_timer.setInterval(interval_ms)
        
        self.logger.info(f"Playback speed changed to {self.playback_speed}x")
    
    def _update_bar_label(self):
        """Update bar index label."""
        self.bar_label.setText(f"Bar: {self.current_bar_idx} / {self.max_bar_idx}")
    
    def _update_bar_info(self):
        """Update bar info panel with debugging information."""
        if self.price_bars is None or self.current_bar_idx >= len(self.price_bars):
            self.bar_info_label.setText("No data")
            return
        
        bar = self.price_bars.iloc[self.current_bar_idx]
        
        # Build info text
        info_lines = [
            f"Bar #{self.current_bar_idx}",
            f"Time: {bar['time']}",
            f"OHLC: {bar['open']:.2f} / {bar['high']:.2f} / {bar['low']:.2f} / {bar['close']:.2f}",
        ]
 
        # Add equity if available
        equity_at_bar = self._get_equity_at_bar(self.current_bar_idx)
        if equity_at_bar is not None:
            info_lines.append(f"Equity: ${equity_at_bar:,.2f}")
        # Add custom tooltip if available
        if self.current_bar_idx in self.bar_tooltips:
            info_lines.append("---")
            info_lines.append(self.bar_tooltips[self.current_bar_idx])
        
        self.bar_info_label.setText("\n".join(info_lines))
    
    def _get_equity_at_bar(self, bar_idx: int) -> Optional[float]:
        """Get equity value at specific bar index."""
        for idx, equity in self.equity_curve:
            if idx == bar_idx:
                return equity
        return None
    
    def _highlight_current_bar(self):
        """Highlight current bar in chart (visual indicator)."""
        # TODO: Add vertical line at current bar position
        # This requires custom drawing on chart view
        pass


class BacktestChartView(QChartView):
    """Custom chart view with hover tooltips and interactions."""
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for tooltips."""
        # TODO: Implement hover tooltip showing bar details
        super().mouseMoveEvent(event)
