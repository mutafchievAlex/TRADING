"""
Backtest UI - Display backtest results in main application

Shows backtest metrics, equity curve, trades table, and provides
export functionality for JSON/CSV/HTML reports.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QHeaderView, QScrollArea, QGroupBox, QGridLayout, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QPointF, QDateTime
from PySide6.QtGui import QColor, QFont

# Try to import chart components, optional for visualization
try:
    from PySide6.QtChart import QChart, QChartView, QLineSeries  # type: ignore
    HAS_CHART = True
except (ImportError, ModuleNotFoundError):  # type: ignore
    HAS_CHART = False
    QChart = None  # type: ignore
    QChartView = None  # type: ignore
    QLineSeries = None  # type: ignore

import pandas as pd
from typing import Dict, Optional, List, Tuple
import logging

# Import custom backtest chart widget
try:
    from .backtest_chart import BacktestChartWidget
    HAS_BACKTEST_CHART = True
except ImportError:
    BacktestChartWidget = None
    HAS_BACKTEST_CHART = False

# Import decision analyzer widget
try:
    from .decision_analyzer_widget import DecisionAnalyzerWidget
    HAS_DECISION_ANALYZER = True
except ImportError:
    DecisionAnalyzerWidget = None
    HAS_DECISION_ANALYZER = False


class BacktestWorker(QThread):
    """Worker thread to run backtest without blocking UI."""
    
    progress = Signal(str)  # Status message
    completed = Signal(dict)  # Result summary
    error = Signal(str)  # Error message
    
    def __init__(self, backtest_engine, strategy_engine, indicator_engine, 
                 risk_engine, pattern_engine):
        super().__init__()
        self.backtest_engine = backtest_engine
        self.strategy_engine = strategy_engine
        self.indicator_engine = indicator_engine
        self.risk_engine = risk_engine
        self.pattern_engine = pattern_engine
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Run backtest in background thread."""
        try:
            self.progress.emit("Loading historical data...")
            
            # Load data
            success = self.backtest_engine.load_historical_data(
                market_data_service=None  # Will be passed from main
            )
            if not success:
                self.error.emit("Failed to load historical data")
                return
            
            self.progress.emit("Running backtest simulation...")
            
            # Run backtest
            success = self.backtest_engine.run_backtest(
                strategy_engine=self.strategy_engine,
                indicator_engine=self.indicator_engine,
                risk_engine=self.risk_engine,
                pattern_engine=self.pattern_engine
            )
            
            if not success:
                self.error.emit("Backtest simulation failed")
                return
            
            self.progress.emit("Backtest completed successfully")
            
            # Emit results
            self.completed.emit({
                'summary': self.backtest_engine.get_summary(),
                'metrics': self.backtest_engine.metrics,
                'trades_df': self.backtest_engine.get_trades_dataframe(),
                'equity_curve': self.backtest_engine.equity_curve,
            })
            
        except Exception as e:
            self.error.emit(f"Backtest error: {str(e)}")
            self.logger.error(f"Backtest worker error: {e}", exc_info=True)


class BacktestWindow(QWidget):
    """
    UI for displaying backtest results.
    
    Sections:
    - Summary cards (net profit, win rate, etc.)
    - Equity curve chart
    - Trades table with detailed data
    - Settings snapshot
    - Export buttons (JSON, CSV, HTML)
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.current_summary = None
        self.current_metrics = None
        self.current_trades_df = None
        self.current_equity_curve = None
        self.current_bar_decisions = None
        self.current_price_bars = None
        self.run_backtest_signal = None  # Will be connected by main.py
        self.export_json_clicked = None  # Will be connected by main.py
        self.export_csv_clicked = None   # Will be connected by main.py
        self.export_html_clicked = None  # Will be connected by main.py
        self.progress_bar = None  # Progress bar for visual feedback
        self.chart_widget = None  # Bar-by-bar chart widget
        self.decision_analyzer = None  # Decision analyzer widget
        self.ui_config = {}  # UI configuration from config.yaml
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI layout."""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("30-Day Backtest Report")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Ready")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
                background-color: #E3F2FD;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #1976D2);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)  # Hidden by default
        layout.addWidget(self.progress_bar)
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 1: Summary
        summary_widget = QWidget()
        summary_layout = QVBoxLayout()
        
        # Bar-by-bar chart (top 60% of summary)
        if HAS_BACKTEST_CHART:
            self.chart_widget = BacktestChartWidget()
            # Connect chart play button to backtest callback
            self.chart_widget.run_backtest_callback = self.on_run_backtest_clicked
            summary_layout.addWidget(self.chart_widget, stretch=3)  # 60% height
        else:
            no_chart_label = QLabel("Bar-by-bar chart unavailable. Install requirements.")
            no_chart_label.setStyleSheet("padding: 10px; background-color: #FFF3CD;")
            summary_layout.addWidget(no_chart_label)
        
        # Summary cards
        self.summary_cards = QWidget()
        self.summary_cards_layout = QGridLayout()
        self.summary_cards.setLayout(self.summary_cards_layout)
        summary_layout.addWidget(self.summary_cards, stretch=2)  # 40% height
        
        # Equity curve (optional - only if QtChart available)
        if HAS_CHART:
            self.chart_view = QChartView()
            summary_layout.addWidget(self.chart_view)
        else:
            self.chart_view = None
            summary_layout.addWidget(QLabel("QtChart not available for equity curve visualization"))
        
        summary_widget.setLayout(summary_layout)
        tabs.addTab(summary_widget, "Summary")
        
        # Tab 2: Trades Table
        trades_widget = QWidget()
        trades_layout = QVBoxLayout()
        
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(0)
        trades_layout.addWidget(self.trades_table)
        
        trades_widget.setLayout(trades_layout)
        tabs.addTab(trades_widget, "Trades")
        
        # Tab 3: Statistics
        stats_widget = QWidget()
        stats_layout = QVBoxLayout()
        
        self.stats_text = QLabel("Run backtest to see detailed statistics")
        self.stats_text.setWordWrap(True)
        stats_layout.addWidget(self.stats_text)
        
        stats_widget.setLayout(stats_layout)
        tabs.addTab(stats_widget, "Statistics")
        
        # Tab 4: Settings
        settings_widget = QWidget()
        settings_layout = QVBoxLayout()
        
        self.settings_text = QLabel("Strategy settings will appear here")
        self.settings_text.setWordWrap(True)
        settings_layout.addWidget(self.settings_text)
        
        settings_widget.setLayout(settings_layout)
        tabs.addTab(settings_widget, "Settings")
        
        # Tab 5: Decision Analyzer (Why No Trade?)
        if HAS_DECISION_ANALYZER:
            self.decision_analyzer = DecisionAnalyzerWidget(self.ui_config)
            # Connect analyzer bar selection to chart
            if self.chart_widget:
                self.decision_analyzer.bar_selected.connect(self._on_analyzer_bar_selected)
            tabs.addTab(self.decision_analyzer, "Why No Trade?")
        else:
            self.decision_analyzer = None
        
        layout.addWidget(tabs)
        
        # Export buttons
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        export_json_btn = QPushButton("Export JSON")
        export_json_btn.clicked.connect(lambda: self.on_export_clicked('json'))
        export_layout.addWidget(export_json_btn)
        
        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(lambda: self.on_export_clicked('csv'))
        export_layout.addWidget(export_csv_btn)
        
        export_html_btn = QPushButton("Export HTML")
        export_html_btn.clicked.connect(lambda: self.on_export_clicked('html'))
        export_layout.addWidget(export_html_btn)
        
        layout.addLayout(export_layout)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def on_run_backtest_clicked(self):
        """Handle backtest run button click."""
        self.status_label.setText("Starting backtest...")
        self.logger.info("Run backtest clicked")
        
        # Show and reset progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Initializing backtest...")
        
        # Call the connected backtest function from main.py
        if self.run_backtest_signal:
            self.run_backtest_signal()
        else:
            self.logger.error("Backtest signal not connected")
            self.status_label.setText("Error: Backtest not connected")
            self.progress_bar.setVisible(False)
    
    def on_export_clicked(self, format_type: str):
        """Handle export button click."""
        self.logger.info(f"Export {format_type} clicked")
        
        # Call the appropriate export function
        if format_type == 'json' and self.export_json_clicked:
            self.export_json_clicked()
        elif format_type == 'csv' and self.export_csv_clicked:
            self.export_csv_clicked()
        elif format_type == 'html' and self.export_html_clicked:
            self.export_html_clicked()
        else:
            self.logger.error(f"Export {format_type} not connected")
            self.status_label.setText(f"Error: Export {format_type} not available")
    
    def update_progress(self, percent: int, message: str):
        """Update progress bar value and text."""
        if self.progress_bar:
            self.progress_bar.setValue(percent)
            self.progress_bar.setFormat(f"{message} ({percent}%)")
            # Force UI update
            self.progress_bar.repaint()
    
    def hide_progress(self):
        """Hide progress bar after completion."""
        if self.progress_bar:
            self.progress_bar.setVisible(False)
    
    def display_results(self, 
                       summary: Dict,
                       metrics: Dict,
                       trades_df: pd.DataFrame,
                       equity_curve: List[Tuple],
                       settings: Dict,
                       price_bars: Optional[pd.DataFrame] = None,
                       bar_tooltips: Optional[Dict[int, str]] = None,
                       bar_decisions: Optional[List[Dict]] = None):
        """
        Display backtest results.
        
        Args:
            summary: Backtest summary dict
            metrics: Metrics dict
            trades_df: Trades DataFrame
            equity_curve: List of (datetime, equity) tuples
            settings: Strategy settings dict
            price_bars: Optional OHLC price bars for chart visualization
            bar_tooltips: Optional debugging tooltips per bar index
            bar_decisions: Optional list of bar decision dicts from backtest_engine
        """
        self.current_summary = summary
        self.current_metrics = metrics
        self.current_trades_df = trades_df
        self.current_equity_curve = equity_curve
        self.current_bar_decisions = bar_decisions
        self.current_price_bars = price_bars
        
        # Load data into bar-by-bar chart
        if self.chart_widget and price_bars is not None:
            # Convert equity_curve to bar_idx format
            equity_by_bar = []
            for idx, (timestamp, equity_val) in enumerate(equity_curve):
                equity_by_bar.append((idx, equity_val))
            
            # Convert trades DataFrame to list of dicts
            trades_list = trades_df.to_dict('records') if not trades_df.empty else []
            
            # Load into chart widget
            self.chart_widget.load_data(
                price_bars=price_bars,
                equity_curve=equity_by_bar,
                trades=trades_list,
                bar_tooltips=bar_tooltips
            )
        
        # Clear existing widgets
        while self.summary_cards_layout.count():
            self.summary_cards_layout.takeAt(0).widget().deleteLater()
        
        # Display summary cards
        self._create_summary_cards(metrics)
        
        # Display equity curve
        self._create_equity_curve(equity_curve)
        
        # Display trades table
        self._display_trades_table(trades_df)
        
        # Display statistics
        self._display_statistics(metrics)
        
        # Display settings
        self._display_settings(settings)
        
        # Load decision analyzer data
        if self.decision_analyzer and bar_decisions and price_bars is not None:
            self.decision_analyzer.load_data(bar_decisions, price_bars)
        
        self.status_label.setText(f"Backtest complete: {metrics.get('total_trades', 0)} trades, "
                                 f"${metrics.get('net_profit', 0):.2f} net profit")
    
    def _create_summary_cards(self, metrics: Dict):
        """Create summary metric cards."""
        cards = [
            ("Total Trades", f"{metrics.get('total_trades', 0)}", None),
            ("Net Profit", f"${metrics.get('net_profit', 0):.2f}", 
             'green' if metrics.get('net_profit', 0) >= 0 else 'red'),
            ("Win Rate", f"{metrics.get('win_rate', 0):.1f}%", None),
            ("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}", None),
            ("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%", 
             'red' if metrics.get('max_drawdown', 0) > 0 else None),
            ("Avg Trade", f"${metrics.get('avg_trade', 0):.2f}", None),
            ("Expectancy", f"${metrics.get('expectancy_per_trade', 0):.2f}", None),
            ("Avg Bars Held", f"{metrics.get('avg_bars_held', 0):.0f}", None),
        ]
        
        for i, (title, value, color) in enumerate(cards):
            row = i // 4
            col = i % 4
            
            card = self._create_card(title, value, color)
            self.summary_cards_layout.addWidget(card, row, col)
    
    def _create_card(self, title: str, value: str, color: Optional[str] = None) -> QGroupBox:
        """Create a single metric card."""
        card = QGroupBox(title)
        layout = QVBoxLayout()
        
        label = QLabel(value)
        font = label.font()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        
        if color == 'green':
            label.setStyleSheet("color: #0f7938;")
        elif color == 'red':
            label.setStyleSheet("color: #d32f2f;")
        
        layout.addWidget(label)
        layout.setAlignment(label, Qt.AlignCenter)
        card.setLayout(layout)
        
        return card
    
    def _create_equity_curve(self, equity_curve: List[Tuple]):
        """Create equity curve chart."""
        try:
            if not HAS_CHART or self.chart_view is None:
                self.logger.info("Chart view not available")
                return
            
            if not equity_curve:
                self.chart_view.setTitle("No equity curve data")
                return
            
            chart = QChart()
            chart.setTitle("Equity Curve")
            
            series = QLineSeries()
            series.setName("Equity")
            
            for i, (time, equity) in enumerate(equity_curve):
                series.append(i, equity)
            
            chart.addSeries(series)
            chart.createDefaultAxes()
            
            self.chart_view.setChart(chart)
            
        except Exception as e:
            self.logger.error(f"Error creating equity curve: {e}")
    
    def _display_trades_table(self, trades_df: pd.DataFrame):
        """Display trades in table."""
        self.trades_table.setRowCount(0)
        self.trades_table.setColumnCount(0)
        
        if trades_df.empty:
            self.trades_table.setColumnCount(1)
            self.trades_table.setHorizontalHeaderLabels(["No trades"])
            return
        
        # Set columns
        columns = list(trades_df.columns)
        self.trades_table.setColumnCount(len(columns))
        self.trades_table.setHorizontalHeaderLabels(columns)
        
        # Populate rows
        self.trades_table.setRowCount(len(trades_df))
        for row_idx, (_, row) in enumerate(trades_df.iterrows()):
            for col_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                
                # Color code PnL
                if 'pnl' in columns[col_idx].lower() and isinstance(val, (int, float)):
                    if val > 0:
                        item.setBackground(QColor(200, 255, 200))
                    elif val < 0:
                        item.setBackground(QColor(255, 200, 200))
                
                self.trades_table.setItem(row_idx, col_idx, item)
        
        # Auto-resize columns
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    
    def _display_statistics(self, metrics: Dict):
        """Display detailed statistics."""
        stats_text = "Backtest Statistics\n\n"
        
        sections = {
            "Performance": [
                'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
                'net_profit', 'gross_profit', 'gross_loss', 'profit_factor'
            ],
            "Trade Analysis": [
                'avg_trade', 'best_trade', 'worst_trade', 'avg_bars_held',
                'max_consecutive_wins', 'max_consecutive_losses'
            ],
            "Risk": [
                'max_drawdown', 'avg_r_multiple', 'expectancy_per_trade'
            ],
            "Costs": [
                'total_costs', 'avg_cost_per_trade'
            ],
        }
        
        for section, keys in sections.items():
            stats_text += f"{section}\n" + "-" * 40 + "\n"
            for key in keys:
                if key in metrics:
                    value = metrics[key]
                    if isinstance(value, float):
                        stats_text += f"  {key}: {value:.2f}\n"
                    else:
                        stats_text += f"  {key}: {value}\n"
            stats_text += "\n"
        
        self.stats_text.setText(stats_text)
    
    def _display_settings(self, settings: Dict):
        """Display strategy settings snapshot."""
        settings_text = "Strategy Settings\n\n"
        
        for key, value in settings.items():
            settings_text += f"{key}: {value}\n"
        
        self.settings_text.setText(settings_text)
    
    def _on_analyzer_bar_selected(self, bar_index: int):
        """
        Handle bar selection from decision analyzer.
        Syncs chart to show the selected bar.
        
        Args:
            bar_index: Selected bar index
        """
        if self.chart_widget and hasattr(self.chart_widget, 'jump_to_bar'):
            self.chart_widget.jump_to_bar(bar_index)
            self.logger.debug(f"Synced chart to bar {bar_index}")
    
    def set_ui_config(self, config: Dict):
        """
        Set UI configuration from config.yaml.
        
        Args:
            config: UI config dict
        """
        self.ui_config = config
        if self.decision_analyzer:
            self.decision_analyzer.config = config
    
    def set_status(self, message: str):
        """Update status message."""
        self.status_label.setText(message)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    window = BacktestWindow()
    window.show()
    sys.exit(app.exec())
