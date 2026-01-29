"""Backward-compatible logger setup imports."""

from .logger import setup_logging, get_logger, set_correlation_id, clear_correlation_id

__all__ = ["setup_logging", "get_logger", "set_correlation_id", "clear_correlation_id"]
