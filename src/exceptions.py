"""
Custom Exception Hierarchy for Trading Application

This module defines domain-specific exceptions to replace generic Exception catches.
Using specific exceptions improves error handling, debugging, and error recovery.

Exception Hierarchy:
    TradingError (base)
    ├── ConnectionError
    │   ├── MT5ConnectionError
    │   └── MT5InitializationError
    ├── DataError
    │   ├── MarketDataError
    │   ├── IndicatorCalculationError
    │   └── InsufficientDataError
    ├── ExecutionError
    │   ├── OrderPlacementError
    │   ├── OrderModificationError
    │   ├── OrderCancellationError
    │   └── InvalidOrderParametersError
    ├── StateError
    │   ├── StateLoadError
    │   ├── StateSaveError
    │   └── StateCorruptionError
    ├── PatternError
    │   └── PatternDetectionError
    └── ConfigurationError
        ├── InvalidConfigError
        └── MissingConfigError
"""


class TradingError(Exception):
    """
    Base exception for all trading-related errors.
    
    All custom exceptions inherit from this class, allowing catch-all
    handling when needed: `except TradingError as e:`
    """
    pass


# Connection-related errors
class ConnectionError(TradingError):
    """Base exception for connection-related errors."""
    pass


class MT5ConnectionError(ConnectionError):
    """MT5 broker connection failed or lost."""
    pass


class MT5InitializationError(ConnectionError):
    """MT5 platform initialization failed."""
    pass


# Data-related errors
class DataError(TradingError):
    """Base exception for data-related errors."""
    pass


class MarketDataError(DataError):
    """Failed to retrieve market data from MT5."""
    pass


class IndicatorCalculationError(DataError):
    """Technical indicator calculation failed."""
    pass


class InsufficientDataError(DataError):
    """Not enough data available for calculation."""
    pass


# Execution-related errors
class ExecutionError(TradingError):
    """Base exception for order execution errors."""
    pass


class OrderPlacementError(ExecutionError):
    """Failed to place order with broker."""
    pass


class OrderModificationError(ExecutionError):
    """Failed to modify existing order."""
    pass


class OrderCancellationError(ExecutionError):
    """Failed to cancel existing order."""
    pass


class InvalidOrderParametersError(ExecutionError):
    """Order parameters are invalid (volume, SL, TP, etc.)."""
    pass


# State management errors
class StateError(TradingError):
    """Base exception for state management errors."""
    pass


class StateLoadError(StateError):
    """Failed to load state from storage."""
    pass


class StateSaveError(StateError):
    """Failed to save state to storage."""
    pass


class StateCorruptionError(StateError):
    """State data is corrupted or invalid."""
    pass


# Pattern detection errors
class PatternError(TradingError):
    """Base exception for pattern detection errors."""
    pass


class PatternDetectionError(PatternError):
    """Failed to detect or validate trading pattern."""
    pass


# Configuration errors
class ConfigurationError(TradingError):
    """Base exception for configuration errors."""
    pass


class InvalidConfigError(ConfigurationError):
    """Configuration contains invalid values."""
    pass


class MissingConfigError(ConfigurationError):
    """Required configuration is missing."""
    pass
