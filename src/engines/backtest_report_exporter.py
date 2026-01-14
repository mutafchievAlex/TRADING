"""
Backtest Report Exporter - Generates JSON, CSV, and HTML reports

Exports backtest results in multiple formats for analysis and sharing.
All reports include metrics, trade details, and summary cards.

Output Location: {app_root}/reports/XAUUSD_H1_backtest_last30d_{YYYYMMDD_HHMM}.{json|csv|html}
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import logging
import webbrowser


class BacktestReportExporter:
    """
    Exports backtest results to JSON, CSV, and HTML formats.
    
    Responsibilities:
    - Generate JSON with metrics and trade details
    - Create CSV for trades table
    - Build self-contained HTML report with charts and styling
    - Save to timestamped files in reports/ directory
    """
    
    def __init__(self, symbol: str = "XAUUSD", timeframe: str = "H1"):
        """
        Initialize exporter.
        
        Args:
            symbol: Trading instrument
            timeframe: Timeframe
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.logger = logging.getLogger(__name__)
        
        # Create reports directory
        self.reports_dir = Path(__file__).parent.parent.parent / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.logger.info(f"Reports directory: {self.reports_dir}")
    
    def generate_filename(self) -> str:
        """
        Generate timestamped filename.
        
        Format: XAUUSD_H1_backtest_last30d_{YYYYMMDD_HHMM}
        """
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M")
        return f"{self.symbol}_{self.timeframe}_backtest_last30d_{timestamp}"
    
    def export_json(self, 
                   summary: Dict,
                   metrics: Dict,
                   trades_df: pd.DataFrame,
                   settings: Dict) -> Optional[Path]:
        """
        Export backtest as JSON.
        
        Args:
            summary: Backtest summary dict
            metrics: Metrics dict
            trades_df: Trades as DataFrame
            settings: Strategy settings
            
        Returns:
            Path to exported file, or None if error
        """
        try:
            filename = self.generate_filename()
            filepath = self.reports_dir / f"{filename}.json"
            
            # Prepare data for JSON
            data = {
                'backtest_info': {
                    'symbol': self.symbol,
                    'timeframe': self.timeframe,
                    'generated_at': datetime.now().isoformat(),
                    'period_days': summary.get('period_days', 30),
                },
                'metrics': metrics,
                'summary': summary,
                'settings': settings,
                'trades': trades_df.to_dict('records') if not trades_df.empty else []
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"JSON export: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting JSON: {e}")
            return None
    
    def export_csv(self,
                  trades_df: pd.DataFrame) -> Optional[Path]:
        """
        Export trades as CSV.
        
        Args:
            trades_df: Trades DataFrame
            
        Returns:
            Path to exported file
        """
        try:
            filename = self.generate_filename()
            filepath = self.reports_dir / f"{filename}_trades.csv"
            
            if not trades_df.empty:
                trades_df.to_csv(filepath, index=False)
                self.logger.info(f"CSV export: {filepath}")
            else:
                self.logger.warning("No trades to export")
            
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting CSV: {e}")
            return None
    
    def export_html(self,
                   summary: Dict,
                   metrics: Dict,
                   trades_df: pd.DataFrame,
                   equity_curve: list,
                   settings: Dict) -> Optional[Path]:
        """
        Export backtest as self-contained HTML report.
        
        Args:
            summary: Backtest summary
            metrics: Metrics dict
            trades_df: Trades DataFrame
            equity_curve: List of (datetime, equity) tuples
            settings: Strategy settings
            
        Returns:
            Path to exported HTML file
        """
        try:
            filename = self.generate_filename()
            filepath = self.reports_dir / f"{filename}.html"
            
            html = self._generate_html(
                summary=summary,
                metrics=metrics,
                trades_df=trades_df,
                equity_curve=equity_curve,
                settings=settings
            )
            
            with open(filepath, 'w') as f:
                f.write(html)
            
            self.logger.info(f"HTML export: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error exporting HTML: {e}")
            return None
    
    def _generate_html(self,
                      summary: Dict,
                      metrics: Dict,
                      trades_df: pd.DataFrame,
                      equity_curve: list,
                      settings: Dict) -> str:
        """Generate HTML report content."""
        
        # Summary cards
        cards_html = f"""
        <div class="cards-row">
            <div class="card">
                <h3>Total Trades</h3>
                <p class="value">{metrics.get('total_trades', 0)}</p>
            </div>
            <div class="card">
                <h3>Net Profit</h3>
                <p class="value profit">${metrics.get('net_profit', 0):.2f}</p>
            </div>
            <div class="card">
                <h3>Win Rate</h3>
                <p class="value">{metrics.get('win_rate', 0):.1f}%</p>
            </div>
            <div class="card">
                <h3>Profit Factor</h3>
                <p class="value">{metrics.get('profit_factor', 0):.2f}</p>
            </div>
            <div class="card">
                <h3>Max Drawdown</h3>
                <p class="value">{metrics.get('max_drawdown', 0):.2f}%</p>
            </div>
        </div>
        """
        
        # Trades table
        trades_html = "<table class='trades-table'><thead><tr>"
        if not trades_df.empty:
            for col in trades_df.columns:
                trades_html += f"<th>{col}</th>"
            trades_html += "</tr></thead><tbody>"
            
            for _, row in trades_df.iterrows():
                trades_html += "<tr>"
                for val in row:
                    trades_html += f"<td>{val}</td>"
                trades_html += "</tr>"
            
            trades_html += "</tbody></table>"
        else:
            trades_html += "<p>No trades</p>"
        
        # Settings snapshot
        settings_html = "<pre>" + json.dumps(settings, indent=2, default=str) + "</pre>"
        
        # Complete HTML document
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Backtest Report - {self.symbol} {self.timeframe}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 30px;
        }}
        h1 {{ color: #1a73e8; margin-bottom: 10px; }}
        .header {{ border-bottom: 2px solid #e0e0e0; padding-bottom: 20px; margin-bottom: 30px; }}
        .timestamp {{ color: #999; font-size: 0.9em; }}
        
        .cards-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            background: #f9f9f9;
        }}
        .card h3 {{ font-size: 0.85em; color: #666; margin-bottom: 10px; }}
        .card .value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #1a73e8;
        }}
        .card .value.profit {{ color: #0f7938; }}
        .card .value.loss {{ color: #d32f2f; }}
        
        section {{
            margin-bottom: 40px;
        }}
        section h2 {{
            color: #1a73e8;
            font-size: 1.2em;
            margin-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 10px;
        }}
        
        .trades-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        .trades-table th {{
            background-color: #f5f5f5;
            color: #333;
            padding: 10px;
            text-align: left;
            border-bottom: 2px solid #e0e0e0;
            font-weight: 600;
        }}
        .trades-table td {{
            padding: 10px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .trades-table tr:hover {{ background-color: #f9f9f9; }}
        
        pre {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            font-size: 0.9em;
            overflow-x: auto;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Backtest Report</h1>
            <p>{self.symbol} | {self.timeframe} | Last 30 Days</p>
            <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <section>
            <h2>Performance Summary</h2>
            {cards_html}
        </section>
        
        <section>
            <h2>Detailed Metrics</h2>
            <pre>{json.dumps(metrics, indent=2, default=str)}</pre>
        </section>
        
        <section>
            <h2>Trades ({metrics.get('total_trades', 0)})</h2>
            {trades_html}
        </section>
        
        <section>
            <h2>Strategy Settings</h2>
            {settings_html}
        </section>
        
        <div class="footer">
            <p>This backtest is for informational purposes only and does not guarantee future results.</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def export_all(self,
                  summary: Dict,
                  metrics: Dict,
                  trades_df: pd.DataFrame,
                  equity_curve: list,
                  settings: Dict) -> Dict[str, Optional[Path]]:
        """
        Export backtest to all formats (JSON, CSV, HTML).
        
        Args:
            summary: Backtest summary
            metrics: Metrics dict
            trades_df: Trades DataFrame
            equity_curve: List of (datetime, equity) tuples
            settings: Strategy settings
            
        Returns:
            Dict with 'json', 'csv', 'html' paths
        """
        self.logger.info("Exporting backtest to all formats...")
        
        return {
            'json': self.export_json(summary, metrics, trades_df, settings),
            'csv': self.export_csv(trades_df),
            'html': self.export_html(summary, metrics, trades_df, equity_curve, settings),
        }
    
    def open_html_report(self, filepath: Path) -> None:
        """
        Open HTML report in default browser.
        
        Args:
            filepath: Path to HTML file
        """
        try:
            webbrowser.open(f"file:///{filepath.absolute()}")
            self.logger.info(f"Opened HTML report in browser: {filepath}")
        except Exception as e:
            self.logger.error(f"Error opening HTML report: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    exporter = BacktestReportExporter(symbol="XAUUSD", timeframe="H1")
    
    # Sample data for testing
    sample_metrics = {
        'total_trades': 5,
        'net_profit': 1250.50,
        'win_rate': 60.0,
        'profit_factor': 2.5,
        'max_drawdown': 15.2
    }
    
    sample_trades_df = pd.DataFrame({
        'trade_id': [1, 2, 3],
        'direction': ['LONG', 'LONG', 'LONG'],
        'entry_price': [2100.0, 2105.0, 2110.0],
        'exit_price': [2110.0, 2103.0, 2115.0],
        'pnl_cash': [500.0, -200.0, 350.0],
        'pnl_percent': [10.0, -4.0, 7.0],
        'tp1_price': [2105.0, 2110.0, 2115.0],
        'tp2_price': [2108.0, 2113.0, 2118.0],
        'tp3_price': [2112.0, 2117.0, 2122.0],
        'tp1_reached': [True, False, True],
        'bars_held_after_tp1': [2, 0, 1],
        'max_extension_after_tp1': [0.5, 0.0, 0.3],
        'tp1_exit_reason': ['HOLD', 'N/A', 'WAIT_NEXT_BAR'],
    })
    
    sample_summary = {
        'symbol': 'XAUUSD',
        'timeframe': 'H1',
        'period_days': 30,
        'starting_equity': 10000.0,
        'final_equity': 11250.50
    }
    
    sample_settings = {
        'risk_percent': 2.0,
        'atr_multiplier_sl': 2.0,
        'rr_long': 2.0,
    }
    
    print("BacktestReportExporter initialized")
    print(f"Reports directory: {exporter.reports_dir}")
