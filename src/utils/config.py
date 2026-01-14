"""
Configuration Management - Centralized config for the trading application

This module handles all configuration settings:
- MT5 connection details
- Trading parameters
- Risk management settings
- UI preferences
"""

import yaml
import json
from pathlib import Path
from typing import Any, Dict
import logging


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
            
            self.logger.info(f"Configuration loaded from {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self._load_defaults()
    
    def _load_defaults(self):
        """Load default configuration values."""
        self._config = {
            'mt5': {
                'login': None,
                'password': None,
                'server': None,
                'terminal_path': None,
                'symbol': 'XAUUSD',
                'timeframe': 'H1',
                'magic_number': 234000
            },
            'strategy': {
                'pivot_lookback_left': 5,
                'pivot_lookback_right': 5,
                'equality_tolerance': 2.0,
                'min_bars_between': 10,
                'atr_multiplier_stop': 2.0,
                'risk_reward_ratio': 2.0,
                'momentum_atr_threshold': 0.5,
                'cooldown_hours': 24,
                'pyramiding': 1
            },
            'risk': {
                'risk_percent': 1.0,
                'commission_per_lot': 0.0,
                'max_drawdown_percent': 10.0
            },
            'data': {
                'bars_to_fetch': 500,
                'state_file': 'data/state.json'
            },
            'logging': {
                'log_dir': 'logs',
                'log_level': 'INFO',
                'max_log_size_mb': 10,
                'backup_count': 5
            },
            'ui': {
                'window_title': 'XAUUSD Double Bottom Strategy',
                'theme': 'dark',
                'refresh_interval_seconds': 10
            },
            'mode': {
                'demo_mode': True,
                'auto_trade': False
            }
        }
        self.logger.info("Default configuration loaded")
    
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
