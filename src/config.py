"""
Core configuration models for MT5, strategy, and risk settings.

Loads configuration from a YAML/JSON file, applies environment overrides,
and validates critical constraints.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import yaml

_LOGGER = logging.getLogger(__name__)


def _coerce_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.lstrip("-").isdigit():
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


@dataclass
class Mt5Config:
    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None
    terminal_path: Optional[str] = None
    symbol: str = "XAUUSD"
    timeframe: str = "H1"
    magic_number: int = 234000

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mt5Config":
        defaults = cls()
        login = _coerce_int(data.get("login", defaults.login))
        magic_number = _coerce_int(data.get("magic_number", defaults.magic_number))
        return cls(
            login=login,
            password=_coerce_str(data.get("password", defaults.password)),
            server=_coerce_str(data.get("server", defaults.server)),
            terminal_path=_coerce_str(data.get("terminal_path", defaults.terminal_path)),
            symbol=_coerce_str(data.get("symbol", defaults.symbol)) or defaults.symbol,
            timeframe=_coerce_str(data.get("timeframe", defaults.timeframe)) or defaults.timeframe,
            magic_number=magic_number or defaults.magic_number,
        )

    def apply_env_overrides(self, env: Mapping[str, str]) -> None:
        login = _coerce_int(env.get("MT5_LOGIN")) if env.get("MT5_LOGIN") else None
        if login is not None:
            self.login = login
        password = env.get("MT5_PASSWORD")
        if password:
            self.password = password
        server = env.get("MT5_SERVER")
        if server:
            self.server = server
        terminal_path = env.get("MT5_TERMINAL_PATH")
        if terminal_path:
            self.terminal_path = terminal_path
        symbol = env.get("MT5_SYMBOL")
        if symbol:
            self.symbol = symbol
        timeframe = env.get("MT5_TIMEFRAME")
        if timeframe:
            self.timeframe = timeframe
        magic_number = _coerce_int(env.get("MT5_MAGIC_NUMBER"))
        if magic_number is not None:
            self.magic_number = magic_number

    def validate(self) -> None:
        if self.magic_number <= 0:
            raise ValueError("mt5.magic_number must be a positive integer.")

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
    pivot_lookback_left: int = 5
    pivot_lookback_right: int = 5
    equality_tolerance: float = 2.0
    min_bars_between: int = 10
    atr_multiplier_stop: float = 2.0
    risk_reward_ratio_long: float = 2.0
    risk_reward_ratio_short: float = 2.0
    momentum_atr_threshold: float = 0.3
    enable_momentum_filter: bool = False
    cooldown_hours: int = 24
    pyramiding: int = 1
    quality_score_threshold: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyConfig":
        defaults = cls()
        rr_default = _coerce_float(data.get("risk_reward_ratio", None))
        risk_reward_ratio_long = _coerce_float(data.get("risk_reward_ratio_long", rr_default))
        risk_reward_ratio_short = _coerce_float(data.get("risk_reward_ratio_short", rr_default))
        return cls(
            pivot_lookback_left=_coerce_int(data.get("pivot_lookback_left", defaults.pivot_lookback_left))
            or defaults.pivot_lookback_left,
            pivot_lookback_right=_coerce_int(data.get("pivot_lookback_right", defaults.pivot_lookback_right))
            or defaults.pivot_lookback_right,
            equality_tolerance=_coerce_float(data.get("equality_tolerance", defaults.equality_tolerance))
            or defaults.equality_tolerance,
            min_bars_between=_coerce_int(data.get("min_bars_between", defaults.min_bars_between))
            or defaults.min_bars_between,
            atr_multiplier_stop=_coerce_float(data.get("atr_multiplier_stop", defaults.atr_multiplier_stop))
            or defaults.atr_multiplier_stop,
            risk_reward_ratio_long=risk_reward_ratio_long or defaults.risk_reward_ratio_long,
            risk_reward_ratio_short=risk_reward_ratio_short or defaults.risk_reward_ratio_short,
            momentum_atr_threshold=_coerce_float(
                data.get("momentum_atr_threshold", defaults.momentum_atr_threshold)
            )
            or defaults.momentum_atr_threshold,
            enable_momentum_filter=_coerce_bool(
                data.get("enable_momentum_filter", defaults.enable_momentum_filter)
            )
            if data.get("enable_momentum_filter", None) is not None
            else defaults.enable_momentum_filter,
            cooldown_hours=_coerce_int(data.get("cooldown_hours", defaults.cooldown_hours))
            or defaults.cooldown_hours,
            pyramiding=_coerce_int(data.get("pyramiding", defaults.pyramiding))
            or defaults.pyramiding,
            quality_score_threshold=_coerce_float(data.get("quality_score_threshold")),
        )

    def apply_env_overrides(self, env: Mapping[str, str]) -> None:
        pyramiding = _coerce_int(env.get("STRATEGY_PYRAMIDING"))
        if pyramiding is not None:
            self.pyramiding = pyramiding
        atr_multiplier_stop = _coerce_float(env.get("STRATEGY_ATR_MULTIPLIER_STOP"))
        if atr_multiplier_stop is not None:
            self.atr_multiplier_stop = atr_multiplier_stop
        rr_long = _coerce_float(env.get("STRATEGY_RR_LONG"))
        if rr_long is not None:
            self.risk_reward_ratio_long = rr_long
        rr_short = _coerce_float(env.get("STRATEGY_RR_SHORT"))
        if rr_short is not None:
            self.risk_reward_ratio_short = rr_short
        momentum_threshold = _coerce_float(env.get("STRATEGY_MOMENTUM_ATR_THRESHOLD"))
        if momentum_threshold is not None:
            self.momentum_atr_threshold = momentum_threshold
        enable_momentum = _coerce_bool(env.get("STRATEGY_ENABLE_MOMENTUM_FILTER"))
        if enable_momentum is not None:
            self.enable_momentum_filter = enable_momentum
        cooldown_hours = _coerce_int(env.get("STRATEGY_COOLDOWN_HOURS"))
        if cooldown_hours is not None:
            self.cooldown_hours = cooldown_hours

    def validate(self) -> None:
        if self.pyramiding < 1:
            raise ValueError("strategy.pyramiding must be >= 1.")
        if self.atr_multiplier_stop <= 0:
            raise ValueError("strategy.atr_multiplier_stop must be > 0.")
        if self.risk_reward_ratio_long <= 0 or self.risk_reward_ratio_short <= 0:
            raise ValueError("strategy risk_reward_ratio values must be > 0.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pivot_lookback_left": self.pivot_lookback_left,
            "pivot_lookback_right": self.pivot_lookback_right,
            "equality_tolerance": self.equality_tolerance,
            "min_bars_between": self.min_bars_between,
            "atr_multiplier_stop": self.atr_multiplier_stop,
            "risk_reward_ratio_long": self.risk_reward_ratio_long,
            "risk_reward_ratio_short": self.risk_reward_ratio_short,
            "momentum_atr_threshold": self.momentum_atr_threshold,
            "enable_momentum_filter": self.enable_momentum_filter,
            "cooldown_hours": self.cooldown_hours,
            "pyramiding": self.pyramiding,
            "quality_score_threshold": self.quality_score_threshold,
        }


@dataclass
class RiskConfig:
    risk_percent: float = 1.0
    commission_per_lot: float = 0.0
    max_drawdown_percent: float = 10.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskConfig":
        defaults = cls()
        return cls(
            risk_percent=_coerce_float(data.get("risk_percent", defaults.risk_percent))
            or defaults.risk_percent,
            commission_per_lot=_coerce_float(data.get("commission_per_lot", defaults.commission_per_lot))
            or defaults.commission_per_lot,
            max_drawdown_percent=_coerce_float(
                data.get("max_drawdown_percent", defaults.max_drawdown_percent)
            )
            or defaults.max_drawdown_percent,
        )

    def apply_env_overrides(self, env: Mapping[str, str]) -> None:
        risk_percent = _coerce_float(env.get("RISK_PERCENT"))
        if risk_percent is not None:
            self.risk_percent = risk_percent
        commission_per_lot = _coerce_float(env.get("RISK_COMMISSION_PER_LOT"))
        if commission_per_lot is not None:
            self.commission_per_lot = commission_per_lot
        max_drawdown = _coerce_float(env.get("RISK_MAX_DRAWDOWN_PERCENT"))
        if max_drawdown is not None:
            self.max_drawdown_percent = max_drawdown

    def validate(self) -> None:
        if self.risk_percent <= 0:
            raise ValueError("risk.risk_percent must be > 0.")
        if self.max_drawdown_percent < 0:
            raise ValueError("risk.max_drawdown_percent must be >= 0.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_percent": self.risk_percent,
            "commission_per_lot": self.commission_per_lot,
            "max_drawdown_percent": self.max_drawdown_percent,
        }


@dataclass
class AppConfig:
    mt5: Mt5Config = field(default_factory=Mt5Config)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        return cls(
            mt5=Mt5Config.from_dict(data.get("mt5", {})),
            strategy=StrategyConfig.from_dict(data.get("strategy", {})),
            risk=RiskConfig.from_dict(data.get("risk", {})),
        )

    def apply_env_overrides(self, env: Mapping[str, str]) -> None:
        self.mt5.apply_env_overrides(env)
        self.strategy.apply_env_overrides(env)
        self.risk.apply_env_overrides(env)

    def validate(self) -> None:
        self.mt5.validate()
        self.strategy.validate()
        self.risk.validate()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mt5": self.mt5.to_dict(),
            "strategy": self.strategy.to_dict(),
            "risk": self.risk.to_dict(),
        }


def _load_config_data(config_file: Path) -> Dict[str, Any]:
    if not config_file.exists():
        _LOGGER.warning("Config file not found: %s. Using defaults.", config_file)
        return {}
    if config_file.suffix in {".yaml", ".yml"}:
        with config_file.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    if config_file.suffix == ".json":
        with config_file.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    raise ValueError(f"Unsupported config file format: {config_file.suffix}")


def load_app_config(config_file: str = "config/config.yaml") -> AppConfig:
    """Load config file, apply env overrides, and validate."""
    config_path = Path(config_file)
    data = _load_config_data(config_path)
    config = AppConfig.from_dict(data)
    config.apply_env_overrides(os.environ)
    config.validate()
    return config
