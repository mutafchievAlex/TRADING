"""
Logger - Comprehensive logging system for the trading application

This module provides centralized logging with:
- Multiple log levels
- File and console output
- Rotation to prevent excessive file sizes
- Structured trade logging
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_correlation_id(value: Optional[str]) -> None:
    """Set correlation ID for the current context."""
    _correlation_id.set(value or "-")


def clear_correlation_id() -> None:
    """Clear correlation ID for the current context."""
    _correlation_id.set("-")


class CorrelationIdFilter(logging.Filter):
    """Inject correlation_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get("-")
        return True


class JsonFormatter(logging.Formatter):
    """JSON formatter with required fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


class TradingLogger:
    """
    Centralized logging system for the trading application.
    
    Features:
    - Separate logs for system events and trades
    - Rotating file handlers
    - Console and file output
    - Configurable log levels
    """
    
    def __init__(self, log_dir: str = "logs", 
                 log_level: str = "INFO",
                 max_bytes: int = 10485760,  # 10MB
                 backup_count: int = 5):
        """
        Initialize logging system.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            max_bytes: Maximum size per log file before rotation
            backup_count: Number of backup files to keep
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        self._setup_loggers()
    
    def _setup_loggers(self):
        """Set up main and trade loggers."""
        
        # Main system logger
        self.main_logger = self._create_logger(
            'trading_system',
            self.log_dir / 'system.log',
            self.log_level
        )
        
        # Trade-specific logger (always INFO level)
        self.trade_logger = self._create_logger(
            'trades',
            self.log_dir / 'trades.log',
            logging.INFO
        )
    
    def _create_logger(self, name: str, log_file: Path, level: int) -> logging.Logger:
        """
        Create a logger with file and console handlers.
        
        Args:
            name: Logger name
            log_file: Path to log file
            level: Logging level
            
        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Prevent duplicate handlers if logger already exists
        if logger.handlers:
            return logger
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Formatter
        formatter = JsonFormatter()
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addFilter(CorrelationIdFilter())
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    @staticmethod
    def _fmt_float(value, default: str = "N/A") -> str:
        """Safely format numeric values for log output."""
        try:
            if value is None:
                return default
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return default
    
    def log_trade(self, trade_data: dict):
        """
        Log a trade event with structured data.
        
        Args:
            trade_data: Dictionary with trade details
        """
        trade_type = trade_data.get('type', 'UNKNOWN')
        timestamp = datetime.now().isoformat()
        
        if trade_type == 'ENTRY':
            self.trade_logger.info(
                f"ENTRY | Ticket: {trade_data.get('ticket')} | "
                f"Price: {self._fmt_float(trade_data.get('entry_price'))} | "
                f"SL: {self._fmt_float(trade_data.get('stop_loss'))} | "
                f"TP: {self._fmt_float(trade_data.get('take_profit'))} | "
                f"Volume: {self._fmt_float(trade_data.get('volume'))} | "
                f"Pattern: {trade_data.get('pattern_type', 'N/A')}"
            )
        elif trade_type == 'EXIT':
            profit_value = self._fmt_float(trade_data.get('profit'))
            profit_display = f"${profit_value}" if profit_value != "N/A" else "N/A"
            self.trade_logger.info(
                f"EXIT | Ticket: {trade_data.get('ticket')} | "
                f"Exit Price: {self._fmt_float(trade_data.get('exit_price'))} | "
                f"Profit: {profit_display} | "
                f"Reason: {trade_data.get('exit_reason')}"
            )
        elif trade_type == 'SIGNAL':
            self.trade_logger.info(
                f"SIGNAL | {trade_data.get('message', 'Entry signal detected')} | "
                f"Price: {self._fmt_float(trade_data.get('price'))}"
            )
    
    def log_decision(self, decision_type: str, message: str, details: dict = None):
        """
        Log a trading decision with reasoning.
        
        Args:
            decision_type: Type of decision (ENTRY_REJECTED, EXIT_SIGNAL, etc.)
            message: Decision message
            details: Additional details dictionary
        """
        detail_str = ""
        if details:
            detail_str = " | " + " | ".join(f"{k}: {v}" for k, v in details.items())
        
        self.main_logger.info(f"DECISION | {decision_type} | {message}{detail_str}")
    
    def get_main_logger(self) -> logging.Logger:
        """Get the main system logger."""
        return self.main_logger
    
    def get_trade_logger(self) -> logging.Logger:
        """Get the trade-specific logger."""
        return self.trade_logger


# Global logger instance
_logger_instance = None


def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> TradingLogger:
    """
    Initialize and return the global logger instance.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        
    Returns:
        TradingLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = TradingLogger(log_dir, log_level)
    return _logger_instance


def get_logger() -> TradingLogger:
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = setup_logging()
    return _logger_instance


if __name__ == "__main__":
    # Test logging
    logger = setup_logging(log_dir="logs", log_level="DEBUG")
    
    main = logger.get_main_logger()
    main.info("System started")
    main.debug("Debug message")
    main.warning("Warning message")
    main.error("Error message")
    
    # Test trade logging
    logger.log_trade({
        'type': 'ENTRY',
        'ticket': 12345,
        'entry_price': 2000.50,
        'stop_loss': 1980.00,
        'take_profit': 2040.00,
        'volume': 0.10,
        'pattern_type': 'Double Bottom'
    })
    
    logger.log_trade({
        'type': 'EXIT',
        'ticket': 12345,
        'exit_price': 2040.00,
        'profit': 395.00,
        'exit_reason': 'Take Profit'
    })
    
    logger.log_decision('ENTRY_REJECTED', 'Momentum insufficient', 
                       {'candle_size': 5.2, 'required': 7.5})
    
    print("Logging test complete. Check logs/ directory.")
