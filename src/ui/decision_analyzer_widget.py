"""
Decision Analyzer Widget - Displays "Why No Trade?" analysis

This widget provides detailed insights into why trades were not taken on specific bars,
showing the decision pipeline breakdown, blocking reasons, and bar context.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QPushButton, QComboBox,
    QGroupBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
import pandas as pd
from typing import Optional, Dict, List
import logging


class DecisionAnalyzerWidget(QWidget):
    """
    Widget for analyzing bar-by-bar trading decisions.
    
    Features:
    - Stage breakdown panel with pass/fail/skipped indicators
    - Blocking reason focus with required vs actual values
    - Bar context panel showing relevant data
    - Reason distribution summary
    - Near-miss detection
    """
    
    bar_selected = Signal(int)  # Emits bar index when user clicks on a decision
    
    def __init__(self, config: Dict, parent=None):
        """
        Initialize Decision Analyzer Widget.
        
        Args:
            config: UI configuration dict from config.yaml
            parent: Parent widget
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.bar_decisions = None
        self.price_data = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header with title and filter controls
        header_layout = QHBoxLayout()
        
        title = QLabel("Why No Trade? Analyzer")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2196F3;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filter by fail code
        self.fail_code_combo = QComboBox()
        self.fail_code_combo.addItem("All Decisions")
        self.fail_code_combo.currentIndexChanged.connect(self._on_filter_changed)
        header_layout.addWidget(QLabel("Filter:"))
        header_layout.addWidget(self.fail_code_combo)
        
        layout.addLayout(header_layout)
        
        # Main content area with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        
        # Reason Distribution Summary
        if self.config.get('reason_distribution_summary', {}).get('enabled', True):
            self.summary_group = self._create_summary_panel()
            content_layout.addWidget(self.summary_group)
        
        # Decisions Table with Stage Breakdown
        self.decisions_table = self._create_decisions_table()
        content_layout.addWidget(self.decisions_table)
        
        # Bar Context Panel (shown when row selected)
        if self.config.get('bar_context_panel', {}).get('enabled', True):
            self.context_panel = self._create_context_panel()
            self.context_panel.hide()
            content_layout.addWidget(self.context_panel)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
    def _create_summary_panel(self) -> QGroupBox:
        """Create reason distribution summary panel."""
        group = QGroupBox("Blocking Reasons Distribution")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #424242;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        self.summary_label = QLabel("No data loaded")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("padding: 10px; color: #888;")
        layout.addWidget(self.summary_label)
        
        group.setLayout(layout)
        return group
    
    def _create_decisions_table(self) -> QTableWidget:
        """Create decisions table with stage breakdown."""
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels([
            "Bar #", "Time", "Decision", "Stage", "Fail Code", "Reason", "Context"
        ])
        
        # Style
        table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                gridline-color: #424242;
                border: 1px solid #424242;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Bar #
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Time
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Decision
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Stage
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Fail Code
        header.setSectionResizeMode(5, QHeaderView.Stretch)          # Reason
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Context
        
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.itemSelectionChanged.connect(self._on_row_selected)
        
        return table
    
    def _create_context_panel(self) -> QGroupBox:
        """Create bar context panel."""
        group = QGroupBox("🔍 Bar Context Details")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #2D2D2D;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #FF9800;
            }
        """)
        
        layout = QVBoxLayout()
        
        self.context_label = QLabel()
        self.context_label.setWordWrap(True)
        self.context_label.setStyleSheet("padding: 10px; color: white; font-family: 'Courier New';")
        layout.addWidget(self.context_label)
        
        group.setLayout(layout)
        return group
    
    def load_data(self, bar_decisions: List[Dict], price_data: pd.DataFrame):
        """
        Load bar decisions data for analysis.
        
        Args:
            bar_decisions: List of decision dicts from BacktestEngine
            price_data: DataFrame with OHLC data indexed by time
        """
        self.bar_decisions = bar_decisions
        self.price_data = price_data
        
        # Update filter combo with available fail codes
        self._update_fail_code_filter()
        
        # Update summary
        self._update_summary()
        
        # Populate table
        self._populate_table()
        
        self.logger.info(f"Loaded {len(bar_decisions)} bar decisions for analysis")
    
    def _update_fail_code_filter(self):
        """Update fail code filter combo box."""
        if not self.bar_decisions:
            return
        
        # Get unique fail codes
        fail_codes = set()
        for decision in self.bar_decisions:
            if decision['decision'] == 'NO_TRADE' and decision.get('fail_code'):
                fail_codes.add(decision['fail_code'])
        
        # Update combo
        self.fail_code_combo.clear()
        self.fail_code_combo.addItem("All Decisions")
        self.fail_code_combo.addItem("TRADE_ALLOWED")
        self.fail_code_combo.addItem("PATTERN_NOT_PRESENT")
        
        for code in sorted(fail_codes):
            if code not in ["PATTERN_NOT_PRESENT"]:
                self.fail_code_combo.addItem(code)
    
    def _update_summary(self):
        """Update reason distribution summary."""
        if not self.bar_decisions:
            self.summary_label.setText("No data loaded")
            return
        
        # Count by fail code
        fail_counts = {}
        total_no_trade = 0
        total_allowed = 0
        
        for decision in self.bar_decisions:
            if decision['decision'] == 'NO_TRADE':
                total_no_trade += 1
                code = decision.get('fail_code', 'UNKNOWN')
                fail_counts[code] = fail_counts.get(code, 0) + 1
            elif decision['decision'] == 'TRADE_ALLOWED':
                total_allowed += 1
        
        # Build summary text
        total_bars = len(self.bar_decisions)
        summary_lines = [
            f"<b>Total Bars Analyzed:</b> {total_bars}",
            f"<b>Trade Allowed:</b> {total_allowed} ({total_allowed/total_bars*100:.1f}%)",
            f"<b>No Trade:</b> {total_no_trade} ({total_no_trade/total_bars*100:.1f}%)",
            "",
            "<b>Blocking Reasons:</b>"
        ]
        
        # Sort by count descending
        sorted_fails = sorted(fail_counts.items(), key=lambda x: x[1], reverse=True)
        
        for code, count in sorted_fails:
            percent = count / total_no_trade * 100 if total_no_trade > 0 else 0
            color = self._get_fail_code_color(code)
            summary_lines.append(
                f"<span style='color: {color};'>▪</span> <b>{code}:</b> {count} ({percent:.1f}%)"
            )
        
        # Near-miss detection
        if self.config.get('near_miss_detection', {}).get('enabled', True):
            near_misses = self._detect_near_misses()
            if near_misses > 0:
                summary_lines.append("")
                summary_lines.append(
                    f"<span style='color: #FF9800;'>⚠</span> <b>Near Misses:</b> {near_misses} bars"
                )
        
        self.summary_label.setText("<br>".join(summary_lines))
    
    def _detect_near_misses(self) -> int:
        """Detect near-miss situations (almost successful trades)."""
        if not self.bar_decisions:
            return 0
        
        thresholds = self.config.get('near_miss_detection', {}).get('thresholds', {})
        breakout_threshold = thresholds.get('breakout_distance_percent', 0.2)
        quality_threshold = thresholds.get('quality_score_delta', 0.5)
        
        near_misses = 0
        
        for decision in self.bar_decisions:
            if decision['decision'] != 'NO_TRADE':
                continue
            
            fail_code = decision.get('fail_code', '')
            
            # Check for near-miss conditions
            if fail_code == 'NO_BREAKOUT_CONFIRMATION':
                # Check if price was close to neckline
                # This would require additional data from decision dict
                near_misses += 1
            elif fail_code == 'QUALITY_GATE_FAIL':
                # Check if quality score was close to threshold
                near_misses += 1
        
        return near_misses
    
    def _populate_table(self, filter_code: Optional[str] = None):
        """
        Populate decisions table.
        
        Args:
            filter_code: Optional fail code to filter by
        """
        if not self.bar_decisions:
            return
        
        self.decisions_table.setRowCount(0)
        
        color_scheme = self.config.get('stage_breakdown_panel', {}).get('color_scheme', {})
        pass_color = color_scheme.get('pass', 'green')
        fail_color = color_scheme.get('fail', 'red')
        
        for decision in self.bar_decisions:
            # Apply filter
            if filter_code and filter_code != "All Decisions":
                if filter_code == "TRADE_ALLOWED":
                    if decision['decision'] != 'TRADE_ALLOWED':
                        continue
                elif filter_code == "PATTERN_NOT_PRESENT":
                    if decision['decision'] != 'PATTERN_NOT_PRESENT':
                        continue
                else:
                    if decision.get('fail_code') != filter_code:
                        continue
            
            row = self.decisions_table.rowCount()
            self.decisions_table.insertRow(row)
            
            # Bar #
            bar_item = QTableWidgetItem(str(decision.get('bar_index', '-')))
            bar_item.setTextAlignment(Qt.AlignCenter)
            self.decisions_table.setItem(row, 0, bar_item)
            
            # Time
            time_item = QTableWidgetItem(str(decision.get('time', '-')))
            self.decisions_table.setItem(row, 1, time_item)
            
            # Decision
            dec_text = decision['decision']
            dec_item = QTableWidgetItem(dec_text)
            dec_item.setTextAlignment(Qt.AlignCenter)
            
            if dec_text == 'TRADE_ALLOWED':
                dec_item.setForeground(QColor(pass_color))
            elif dec_text == 'NO_TRADE':
                dec_item.setForeground(QColor(fail_color))
            else:
                dec_item.setForeground(QColor('#888'))
            
            self.decisions_table.setItem(row, 2, dec_item)
            
            # Stage
            stage_item = QTableWidgetItem(decision.get('stage', '-'))
            self.decisions_table.setItem(row, 3, stage_item)
            
            # Fail Code
            fail_code = decision.get('fail_code', '-')
            fail_item = QTableWidgetItem(fail_code)
            if fail_code != '-':
                fail_item.setForeground(QColor(self._get_fail_code_color(fail_code)))
            self.decisions_table.setItem(row, 4, fail_item)
            
            # Reason
            reason = decision.get('fail_message', '-')
            reason_item = QTableWidgetItem(reason)
            self.decisions_table.setItem(row, 5, reason_item)
            
            # Context button
            context_btn_item = QTableWidgetItem("CTX")
            context_btn_item.setTextAlignment(Qt.AlignCenter)
            self.decisions_table.setItem(row, 6, context_btn_item)
    
    def _get_fail_code_color(self, fail_code: str) -> str:
        """Get color for fail code."""
        color_map = {
            'PATTERN_NOT_PRESENT': '#888888',
            'NO_BREAKOUT_CONFIRMATION': '#FF9800',
            'TREND_FILTER_BLOCK': '#F44336',
            'MOMENTUM_TOO_WEAK': '#9C27B0',
            'QUALITY_GATE_FAIL': '#FF5722',
            'EXECUTION_GUARD_BLOCK': '#E91E63',
            'RISK_MODEL_FAIL': '#FF1744',
            'UNKNOWN_BLOCK': '#607D8B',
        }
        return color_map.get(fail_code, '#888888')
    
    def _on_filter_changed(self, index: int):
        """Handle filter combo change."""
        filter_text = self.fail_code_combo.currentText()
        self._populate_table(filter_text)
    
    def _on_row_selected(self):
        """Handle row selection in decisions table."""
        selected = self.decisions_table.selectedItems()
        if not selected:
            self.context_panel.hide()
            return
        
        row = selected[0].row()
        
        # Get decision for this row
        bar_index_item = self.decisions_table.item(row, 0)
        if not bar_index_item:
            return
        
        try:
            bar_index = int(bar_index_item.text())
        except:
            return
        
        # Find decision
        decision = None
        for dec in self.bar_decisions:
            if dec.get('bar_index') == bar_index:
                decision = dec
                break
        
        if not decision:
            return
        
        # Show context panel
        self._show_context_details(decision, bar_index)
        
        # Emit signal for chart sync
        self.bar_selected.emit(bar_index)
    
    def _show_context_details(self, decision: Dict, bar_index: int):
        """
        Show detailed context for selected bar.
        
        Args:
            decision: Decision dict
            bar_index: Bar index
        """
        if not self.config.get('bar_context_panel', {}).get('enabled', True):
            return
        
        fields = self.config.get('bar_context_panel', {}).get('fields', [])
        
        # Get bar data
        if self.price_data is not None and bar_index < len(self.price_data):
            bar = self.price_data.iloc[bar_index]
            
            context_lines = [f"<b style='font-size: 14px;'>Bar #{bar_index}</b>", ""]
            
            # ===== FINAL DECISION STATE =====
            context_lines.append("<b style='color: #2196F3; font-size: 13px;'>🎯 FINAL DECISION STATE:</b>")
            context_lines.append("<hr style='border: 1px solid #424242;'>")
            
            dec_timestamp = decision.get('decision_timestamp', decision.get('time', '-'))
            dec_source = decision.get('decision_source', 'Backtest')
            dec_summary = decision.get('decision_summary', decision['decision'])
            
            color_scheme = self.config.get('stage_breakdown_panel', {}).get('color_scheme', {})
            pass_color = color_scheme.get('pass', 'green')
            fail_color = color_scheme.get('fail', 'red')
            
            dec_color = pass_color if decision['decision'] == 'TRADE_ALLOWED' else fail_color
            
            context_lines.append(f"  <b>Decision:</b> <span style='color: {dec_color}; font-weight: bold; font-size: 13px;'>{dec_summary}</span>")
            context_lines.append(f"  <b>Timestamp:</b> {dec_timestamp}")
            context_lines.append(f"  <b>Source:</b> {dec_source}")
            
            if decision['decision'] == 'NO_TRADE':
                fail_code = decision.get('fail_code', '-')
                reason = decision.get('fail_message', '-')
                context_lines.append(f"  <b>Reason:</b> <span style='color: {fail_color};'>{fail_code}</span>")
                context_lines.append(f"  <b>Details:</b> {reason}")
            
            context_lines.append("")
            
            # ===== POSITION INTENT / PREVIEW =====
            if decision['decision'] == 'TRADE_ALLOWED':
                context_lines.append("<b style='color: #4CAF50; font-size: 13px;'>POSITION PREVIEW:</b>")
                context_lines.append("<hr style='border: 1px solid #424242;'>")
                
                entry = decision.get('planned_entry', None)
                sl = decision.get('planned_sl', None)
                tp1 = decision.get('planned_tp1', None)
                tp2 = decision.get('planned_tp2', None)
                tp3 = decision.get('planned_tp3', None)
                risk_usd = decision.get('calculated_risk_usd', None)
                rr = decision.get('calculated_rr', None)
                position_size = decision.get('position_size', None)
                
                if entry:
                    context_lines.append(f"  <b>Planned Entry Price:</b> <span style='color: #2196F3;'>{entry:.2f}</span>")
                if sl:
                    context_lines.append(f"  <b>Planned SL:</b> <span style='color: #F44336;'>{sl:.2f}</span>")
                if tp1:
                    context_lines.append(f"  <b>Planned TP1:</b> <span style='color: #4CAF50;'>{tp1:.2f}</span> (50%)")
                if tp2:
                    context_lines.append(f"  <b>Planned TP2:</b> <span style='color: #4CAF50;'>{tp2:.2f}</span> (75%)")
                if tp3:
                    context_lines.append(f"  <b>Planned TP3:</b> <span style='color: #4CAF50;'>{tp3:.2f}</span> (100%)")
                if risk_usd:
                    context_lines.append(f"  <b>Calculated Risk:</b> <span style='color: #FF9800;'>${risk_usd:.2f}</span>")
                if rr:
                    context_lines.append(f"  <b>Risk:Reward Ratio:</b> <span style='color: #2196F3;'>1:{rr:.1f}</span>")
                if position_size:
                    context_lines.append(f"  <b>Position Size:</b> {position_size:.2f} lots")
                
                context_lines.append("")
            
            # ===== QUALITY GATE / SCORE BREAKDOWN =====
            quality_score = decision.get('entry_quality_score', None)
            quality_breakdown = decision.get('quality_breakdown', None)
            
            if quality_score is not None:
                context_lines.append("<b style='color: #FF9800; font-size: 13px;'>⭐ ENTRY QUALITY SCORE:</b>")
                context_lines.append("<hr style='border: 1px solid #424242;'>")
                
                # Overall score with color coding
                if quality_score >= 7.0:
                    score_color = "#4CAF50"  # Green
                elif quality_score >= 5.0:
                    score_color = "#FF9800"  # Orange
                else:
                    score_color = "#F44336"  # Red
                
                context_lines.append(f"  <b>Overall Quality:</b> <span style='color: {score_color}; font-weight: bold; font-size: 14px;'>{quality_score:.1f} / 10</span>")
                
                if quality_breakdown:
                    context_lines.append(f"  <b>Breakdown:</b>")
                    for component, score in quality_breakdown.items():
                        # Color code each component
                        if score >= 7.0:
                            comp_color = "#4CAF50"
                        elif score >= 5.0:
                            comp_color = "#FF9800"
                        else:
                            comp_color = "#F44336"
                        
                        context_lines.append(f"    • <b>{component.capitalize()}:</b> <span style='color: {comp_color};'>{score:.1f}</span>")
                
                context_lines.append("")
            
            # ===== BAR-CLOSE / GUARD STATUS =====
            context_lines.append("<b style='color: #9C27B0; font-size: 13px;'>BAR-CLOSE GUARD STATUS:</b>")
            context_lines.append("<hr style='border: 1px solid #424242;'>")
            
            last_closed_bar = decision.get('last_closed_bar_time', dec_timestamp)
            using_closed = decision.get('using_closed_bar', True)
            tick_noise = decision.get('tick_noise_filter_passed', True)
            anti_fomo = decision.get('anti_fomo_passed', True)
            
            context_lines.append(f"  <b>Last Closed Bar Time:</b> {last_closed_bar}")
            
            guard_color = "#4CAF50" if using_closed else "#F44336"
            context_lines.append(f"  <b>Using Closed Bar:</b> <span style='color: {guard_color};'>{'PASS' if using_closed else 'FAIL'}</span>")
            
            tick_color = "#4CAF50" if tick_noise else "#F44336"
            context_lines.append(f"  <b>Tick Noise Filter:</b> <span style='color: {tick_color};'>{'PASS' if tick_noise else 'FAIL'}</span>")
            
            fomo_color = "#4CAF50" if anti_fomo else "#F44336"
            context_lines.append(f"  <b>Anti-FOMO:</b> <span style='color: {fomo_color};'>{'PASS' if anti_fomo else 'FAIL'}</span>")
            
            context_lines.append("")
            
            # ===== STAGE CHECKLIST PANEL =====
            if self.config.get('stage_breakdown_panel', {}).get('enabled', True):
                context_lines.append("<b style='color: #FF9800; font-size: 13px;'>8-STAGE DECISION PIPELINE:</b>")
                context_lines.append("<hr style='border: 1px solid #424242;'>")
                
                # Define all 8 stages
                stages = [
                    ("1", "PATTERN_DETECTION"),
                    ("2", "PATTERN_QUALITY"),
                    ("3", "BREAKOUT_CONFIRMATION"),
                    ("4", "TREND_FILTER"),
                    ("5", "MOMENTUM_FILTER"),
                    ("6", "QUALITY_GATE"),
                    ("7", "EXECUTION_GUARDS"),
                    ("8", "RISK_MODEL")
                ]
                
                current_stage = decision.get('stage', '')
                fail_code = decision.get('fail_code', '')
                is_allowed = decision['decision'] == 'TRADE_ALLOWED'
                
                skip_color = color_scheme.get('skipped', 'gray')
                
                for num, stage_name in stages:
                    # Determine stage status
                    if is_allowed:
                        # All stages passed
                        status = "PASS"
                        color = pass_color
                        status_text = "PASS"
                    elif stage_name == current_stage:
                        # This stage failed
                        status = "FAIL"
                        color = fail_color
                        status_text = f"FAIL - {fail_code}"
                    elif self._stage_order(stage_name) < self._stage_order(current_stage):
                        # Stage passed (before failure)
                        status = "PASS"
                        color = pass_color
                        status_text = "PASS"
                    else:
                        # Stage not evaluated (after failure)
                        status = "SKIPPED"
                        color = skip_color
                        status_text = "SKIPPED"
                    
                    context_lines.append(
                        f"  <span style='color: {color};'>{status} <b>Stage {num}:</b> {stage_name} - {status_text}</span>"
                    )
                
                context_lines.append("")
            
            # ===== BAR CONTEXT (OHLC, Indicators) =====
            context_lines.append("<b style='font-size: 13px;'>BAR DATA & INDICATORS:</b>")
            context_lines.append("<hr style='border: 1px solid #424242;'>")
            
            for field in fields:
                if field == 'time':
                    context_lines.append(f"  <b>Time:</b> {decision.get('time', '-')}")
                elif field == 'close_price' and 'close' in bar:
                    context_lines.append(f"  <b>Close:</b> {bar['close']:.2f}")
                elif field == 'atr' and 'atr14' in bar:
                    context_lines.append(f"  <b>ATR14:</b> {bar['atr14']:.2f}")
                elif field == 'neckline_distance':
                    context_lines.append(f"  <b>Neckline Distance:</b> N/A")
                elif field == 'cooldown_status':
                    context_lines.append(f"  <b>Cooldown:</b> N/A")
                elif field == 'regime':
                    if 'ema50' in bar and 'ema200' in bar:
                        regime = "Bullish" if bar['ema50'] > bar['ema200'] else "Bearish"
                        regime_color = "#4CAF50" if regime == "Bullish" else "#F44336"
                        context_lines.append(f"  <b>Regime:</b> <span style='color: {regime_color};'>{regime}</span>")
            
            # Show OHLC data
            if 'open' in bar and 'high' in bar and 'low' in bar and 'close' in bar:
                context_lines.append(f"  <b>Open:</b> {bar['open']:.2f}")
                context_lines.append(f"  <b>High:</b> {bar['high']:.2f}")
                context_lines.append(f"  <b>Low:</b> {bar['low']:.2f}")
                context_lines.append(f"  <b>Close:</b> {bar['close']:.2f}")
            
            # Show EMAs
            if 'ema50' in bar and 'ema200' in bar:
                context_lines.append(f"  <b>EMA50:</b> {bar['ema50']:.2f}")
                context_lines.append(f"  <b>EMA200:</b> {bar['ema200']:.2f}")
            
            self.context_label.setText("<br>".join(context_lines))
            self.context_panel.show()
        else:
            self.context_panel.hide()
    
    def _stage_order(self, stage_name: str) -> int:
        """Return the order index of a stage (1-8)."""
        stages_order = {
            "PATTERN_DETECTION": 1,
            "PATTERN_QUALITY": 2,
            "BREAKOUT_CONFIRMATION": 3,
            "TREND_FILTER": 4,
            "MOMENTUM_FILTER": 5,
            "QUALITY_GATE": 6,
            "EXECUTION_GUARDS": 7,
            "RISK_MODEL": 8
        }
        return stages_order.get(stage_name, 999)
    
    def clear(self):
        """Clear all data."""
        self.bar_decisions = None
        self.price_data = None
        self.decisions_table.setRowCount(0)
        self.summary_label.setText("No data loaded")
        self.context_panel.hide()
