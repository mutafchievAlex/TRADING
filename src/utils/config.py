"""
Configuration Management - Centralized config for the trading application

This module handles all configuration settings:
- MT5 connection details
- Trading parameters
- Risk management settings
- UI preferences
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

_VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _validate_range(
    value: Optional[float],
    *,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> Optional[float]:
    if value is None:
        return None
    if min_value is not None and value < min_value:
        return None
    if max_value is not None and value > max_value:
        return None
    return value


def _default_config_dict() -> Dict[str, Any]:
    return {
        "mt5": {
            "login": None,
            "password": None,
            "server": None,
            "terminal_path": None,
            "symbol": "XAUUSD",
            "timeframe": "H1",
            "magic_number": 234000,
        },
        "strategy": {
            "pivot_lookback_left": 5,
            "pivot_lookback_right": 5,
            "equality_tolerance": 2.0,
            "min_bars_between": 10,
            "atr_multiplier_stop": 2.0,
            "risk_reward_ratio": 2.0,
            "momentum_atr_threshold": 0.3,
            "cooldown_hours": 24,
            "pyramiding": 1,
        },
        "risk": {
            "risk_percent": 1.0,
            "commission_per_lot": 0.0,
            "max_drawdown_percent": 10.0,
        },
        "data": {
            "bars_to_fetch": 500,
            "state_file": "data/state.json",
            "storage_backend": "file",
            "db_url": "sqlite:///data/state.db",
            "backup_dir": "data/backups",
        },
        "logging": {
            "log_dir": "logs",
            "log_level": "INFO",
            "max_log_size_mb": 10,
            "backup_count": 5,
        },
        "ui": {
            "window_title": "XAUUSD Double Bottom Strategy",
            "theme": "dark",
            "refresh_interval_seconds": 10,
        },
        "mode": {
            "demo_mode": True,
            "auto_trade": False,
        },
    }


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


@dataclass
class Mt5Config:
    login: Optional[int]
    password: Optional[str]
    server: Optional[str]
    terminal_path: Optional[str]
    symbol: str
    timeframe: str
    magic_number: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any], logger: logging.Logger) -> "Mt5Config":
        defaults = _default_config_dict()["mt5"]
        login = _coerce_int(data.get("login", defaults["login"]))
        password = _coerce_str(data.get("password", defaults["password"]))
        server = _coerce_str(data.get("server", defaults["server"]))
        terminal_path = _coerce_str(
            data.get("terminal_path", defaults["terminal_path"])
        )
        symbol = _coerce_str(data.get("symbol", defaults["symbol"])) or defaults["symbol"]
        timeframe = (
            _coerce_str(data.get("timeframe", defaults["timeframe"]))
            or defaults["timeframe"]
        )
        magic_number = (
            _coerce_int(data.get("magic_number", defaults["magic_number"]))
            or defaults["magic_number"]
        )
        config = cls(
            login=login,
            password=password,
            server=server,
            terminal_path=terminal_path,
            symbol=symbol,
            timeframe=timeframe,
            magic_number=magic_number,
        )
        config.apply_env_overrides(logger)
        config.validate(logger)
        return config

    def apply_env_overrides(self, logger: logging.Logger) -> None:
        env_login = os.getenv("MT5_LOGIN")
        if env_login:
            coerced = _coerce_int(env_login)
            if coerced is None:
                logger.warning("MT5_LOGIN environment override is not a valid integer.")
            else:
                self.login = coerced
        env_password = os.getenv("MT5_PASSWORD")
        if env_password:
            self.password = env_password
        env_server = os.getenv("MT5_SERVER")
        if env_server:
            self.server = env_server
        env_terminal_path = os.getenv("MT5_TERMINAL_PATH")
        if env_terminal_path:
            self.terminal_path = env_terminal_path

    def validate(self, logger: logging.Logger) -> None:
        if self.login is None:
            self.login = _default_config_dict()["mt5"]["login"]
        if self.magic_number is None:
            self.magic_number = _default_config_dict()["mt5"]["magic_number"]

        missing_fields = []
        if not self.login:
            missing_fields.append("login")
        if not self.password:
            missing_fields.append("password")
        if not self.server:
            missing_fields.append("server")
        if not self.terminal_path:
            missing_fields.append("terminal_path")
        if missing_fields:
            logger.warning(
                "Missing required MT5 configuration fields: %s",
                ", ".join(missing_fields),
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "login": self.login,
            "password": self.password,
            "server": self.server,
            "terminal_path": self.terminal_path,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "magic_number": self.magic_number,
        }


@dataclass
class StrategyConfig:
    pivot_lookback_left: int
    pivot_lookback_right: int
    equality_tolerance: float
    min_bars_between: int
    atr_multiplier_stop: float
    risk_reward_ratio: float
    momentum_atr_threshold: float
    cooldown_hours: float
    pyramiding: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any], logger: logging.Logger) -> "StrategyConfig":
        defaults = _default_config_dict()["strategy"]
        pivot_lookback_left = (
            _coerce_int(data.get("pivot_lookback_left", defaults["pivot_lookback_left"]))
            or defaults["pivot_lookback_left"]
        )
        pivot_lookback_right = (
            _coerce_int(
                data.get("pivot_lookback_right", defaults["pivot_lookback_right"])
            )
            or defaults["pivot_lookback_right"]
        )
        equality_tolerance = (
            _coerce_float(data.get("equality_tolerance", defaults["equality_tolerance"]))
            or defaults["equality_tolerance"]
        )
        min_bars_between = (
            _coerce_int(data.get("min_bars_between", defaults["min_bars_between"]))
            or defaults["min_bars_between"]
        )
        atr_multiplier_stop = (
            _coerce_float(data.get("atr_multiplier_stop", defaults["atr_multiplier_stop"]))
            or defaults["atr_multiplier_stop"]
        )
        risk_reward_ratio = (
            _coerce_float(data.get("risk_reward_ratio", defaults["risk_reward_ratio"]))
            or defaults["risk_reward_ratio"]
        )
        momentum_atr_threshold = (
            _coerce_float(
                data.get("momentum_atr_threshold", defaults["momentum_atr_threshold"])
            )
            or defaults["momentum_atr_threshold"]
        )
        cooldown_hours = (
            _coerce_float(data.get("cooldown_hours", defaults["cooldown_hours"]))
            or defaults["cooldown_hours"]
        )
        pyramiding = (
            _coerce_int(data.get("pyramiding", defaults["pyramiding"]))
            or defaults["pyramiding"]
        )

        cooldown_hours = _validate_range(cooldown_hours, min_value=0)
        if cooldown_hours is None:
            logger.warning(
                "Invalid strategy.cooldown_hours; using default of %s.",
                defaults["cooldown_hours"],
            )
            cooldown_hours = defaults["cooldown_hours"]

        return cls(
            pivot_lookback_left=pivot_lookback_left,
            pivot_lookback_right=pivot_lookback_right,
            equality_tolerance=equality_tolerance,
            min_bars_between=min_bars_between,
            atr_multiplier_stop=atr_multiplier_stop,
            risk_reward_ratio=risk_reward_ratio,
            momentum_atr_threshold=momentum_atr_threshold,
            cooldown_hours=cooldown_hours,
            pyramiding=pyramiding,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pivot_lookback_left": self.pivot_lookback_left,
            "pivot_lookback_right": self.pivot_lookback_right,
            "equality_tolerance": self.equality_tolerance,
            "min_bars_between": self.min_bars_between,
            "atr_multiplier_stop": self.atr_multiplier_stop,
            "risk_reward_ratio": self.risk_reward_ratio,
            "momentum_atr_threshold": self.momentum_atr_threshold,
            "cooldown_hours": self.cooldown_hours,
            "pyramiding": self.pyramiding,
        }


@dataclass
class RiskConfig:
    risk_percent: float
    commission_per_lot: float
    max_drawdown_percent: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any], logger: logging.Logger) -> "RiskConfig":
        defaults = _default_config_dict()["risk"]
        risk_percent = _coerce_float(data.get("risk_percent", defaults["risk_percent"]))
        risk_percent = _validate_range(risk_percent, min_value=0.01, max_value=100.0)
        if risk_percent is None:
            logger.warning(
                "Invalid risk.risk_percent; using default of %s.",
                defaults["risk_percent"],
            )
            risk_percent = defaults["risk_percent"]
        commission_per_lot = (
            _coerce_float(data.get("commission_per_lot", defaults["commission_per_lot"]))
            or defaults["commission_per_lot"]
        )
        max_drawdown_percent = _coerce_float(
            data.get("max_drawdown_percent", defaults["max_drawdown_percent"])
        )
        max_drawdown_percent = _validate_range(
            max_drawdown_percent, min_value=0.0, max_value=100.0
        )
        if max_drawdown_percent is None:
            logger.warning(
                "Invalid risk.max_drawdown_percent; using default of %s.",
                defaults["max_drawdown_percent"],
            )
            max_drawdown_percent = defaults["max_drawdown_percent"]

        return cls(
            risk_percent=risk_percent,
            commission_per_lot=commission_per_lot,
            max_drawdown_percent=max_drawdown_percent,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_percent": self.risk_percent,
            "commission_per_lot": self.commission_per_lot,
            "max_drawdown_percent": self.max_drawdown_percent,
        }


@dataclass
class LoggingConfig:
    log_dir: str
    log_level: str
    max_log_size_mb: int
    backup_count: int

    @classmethod
    def from_dict(cls, data: Dict[str, Any], logger: logging.Logger) -> "LoggingConfig":
        defaults = _default_config_dict()["logging"]
        log_dir = _coerce_str(data.get("log_dir", defaults["log_dir"])) or defaults[
            "log_dir"
        ]
        log_level_raw = (
            _coerce_str(data.get("log_level", defaults["log_level"]))
            or defaults["log_level"]
        )
        log_level = log_level_raw.upper()
        if log_level not in _VALID_LOG_LEVELS:
            logger.warning(
                "Invalid logging.log_level; using default of %s.",
                defaults["log_level"],
            )
            log_level = defaults["log_level"]
        max_log_size_mb = (
            _coerce_int(data.get("max_log_size_mb", defaults["max_log_size_mb"]))
            or defaults["max_log_size_mb"]
        )
        backup_count = (
            _coerce_int(data.get("backup_count", defaults["backup_count"]))
            or defaults["backup_count"]
        )
        if max_log_size_mb <= 0:
            logger.warning(
                "Invalid logging.max_log_size_mb; using default of %s.",
                defaults["max_log_size_mb"],
            )
            max_log_size_mb = defaults["max_log_size_mb"]
        if backup_count < 0:
            logger.warning(
                "Invalid logging.backup_count; using default of %s.",
                defaults["backup_count"],
            )
            backup_count = defaults["backup_count"]

        return cls(
            log_dir=log_dir,
            log_level=log_level,
            max_log_size_mb=max_log_size_mb,
            backup_count=backup_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "log_dir": self.log_dir,
            "log_level": self.log_level,
            "max_log_size_mb": self.max_log_size_mb,
            "backup_count": self.backup_count,
        }


@dataclass
class ModeConfig:
    demo_mode: bool
    auto_trade: bool

    @classmethod
    def from_dict(cls, data: Dict[str, Any], logger: logging.Logger) -> "ModeConfig":
        defaults = _default_config_dict()["mode"]
        demo_mode = data.get("demo_mode", defaults["demo_mode"])
        auto_trade = data.get("auto_trade", defaults["auto_trade"])
        if not isinstance(demo_mode, bool):
            logger.warning(
                "Invalid mode.demo_mode; using default of %s.",
                defaults["demo_mode"],
            )
            demo_mode = defaults["demo_mode"]
        if not isinstance(auto_trade, bool):
            logger.warning(
                "Invalid mode.auto_trade; using default of %s.",
                defaults["auto_trade"],
            )
            auto_trade = defaults["auto_trade"]
        return cls(demo_mode=demo_mode, auto_trade=auto_trade)

    def to_dict(self) -> Dict[str, Any]:
        return {"demo_mode": self.demo_mode, "auto_trade": self.auto_trade}


class Config:
    """
    Configuration manager for the trading application.
    
    Loads settings from YAML or JSON files and provides
    easy access to configuration values.
    """
    
    def __init__(self, config_file: str = "config/config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file
        """
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        self._config: Dict[str, Any] = {}
        
        self.load_config()
    
    def load_config(self):
        """Load configuration from file."""
        try:
            if not self.config_file.exists():
                self.logger.warning(f"Config file not found: {self.config_file}")
                self._load_defaults()
                self.save_config()
                return
            
            # Load based on file extension
            if self.config_file.suffix in ['.yaml', '.yml']:
                with open(self.config_file, 'r') as f:
                    self._config = yaml.safe_load(f) or {}
            elif self.config_file.suffix == '.json':
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {self.config_file.suffix}")
            
            self._apply_schema()
            self.logger.info(f"Configuration loaded from {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self._load_defaults()
    
    def _load_defaults(self):
        """Load default configuration values."""
        self._config = _default_config_dict()
        self._apply_schema()
        self.logger.info("Default configuration loaded")

    def _apply_schema(self):
        defaults = _default_config_dict()
        merged_config = _deep_merge(defaults, self._config or {})
        mt5 = Mt5Config.from_dict(merged_config.get("mt5", {}), self.logger)
        strategy = StrategyConfig.from_dict(
            merged_config.get("strategy", {}), self.logger
        )
        risk = RiskConfig.from_dict(merged_config.get("risk", {}), self.logger)
        logging_config = LoggingConfig.from_dict(
            merged_config.get("logging", {}), self.logger
        )
        mode = ModeConfig.from_dict(merged_config.get("mode", {}), self.logger)

        merged_config["mt5"] = mt5.to_dict()
        merged_config["strategy"] = strategy.to_dict()
        merged_config["risk"] = risk.to_dict()
        merged_config["logging"] = logging_config.to_dict()
        merged_config["mode"] = mode.to_dict()

        self._config = merged_config
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save based on file extension
            if self.config_file.suffix in ['.yaml', '.yml']:
                with open(self.config_file, 'w') as f:
                    yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)
            elif self.config_file.suffix == '.json':
                with open(self.config_file, 'w') as f:
                    json.dump(self._config, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'mt5.symbol')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        try:
            keys = key.split('.')
            value = self._config
            
            for k in keys:
                value = value[k]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'mt5.symbol')
            value: Value to set
        """
        try:
            keys = key.split('.')
            config = self._config
            
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            config[keys[-1]] = value
            
        except Exception as e:
            self.logger.error(f"Error setting config value: {e}")
    
    # Convenience methods for common settings
    
    @property
    def mt5_symbol(self) -> str:
        return self.get('mt5.symbol', 'XAUUSD')
    
    @property
    def mt5_timeframe(self) -> str:
        return self.get('mt5.timeframe', 'H1')
    
    @property
    def is_demo_mode(self) -> bool:
        return self.get('mode.demo_mode', True)
    
    @property
    def auto_trade_enabled(self) -> bool:
        return self.get('mode.auto_trade', False)
    
    @property
    def risk_percent(self) -> float:
        return self.get('risk.risk_percent', 1.0)
    
    def get_mt5_config(self) -> Dict:
        """Get MT5 connection configuration."""
        return self.get('mt5', {})
    
    def get_strategy_config(self) -> Dict:
        """Get strategy parameters."""
        return self.get('strategy', {})
    
    def get_risk_config(self) -> Dict:
        """Get risk management settings."""
        return self.get('risk', {})


# Global config instance
_config_instance = None


def load_config(config_file: str = "config/config.yaml") -> Config:
    """
    Load and return the global configuration instance.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file)
    return _config_instance


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance


if __name__ == "__main__":
    # Test configuration
    logging.basicConfig(level=logging.DEBUG)
    
    config = load_config("config/test_config.yaml")
    
    print("Configuration loaded")
    print(f"  Symbol: {config.mt5_symbol}")
    print(f"  Timeframe: {config.mt5_timeframe}")
    print(f"  Risk %: {config.risk_percent}")
    print(f"  Demo mode: {config.is_demo_mode}")
    
    # Test setting values
    config.set('mt5.symbol', 'EURUSD')
    print(f"  Symbol after change: {config.mt5_symbol}")
    
    # Save config
    config.save_config()
    print("Configuration saved")
