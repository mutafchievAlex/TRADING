"""
Runtime Mode Manager - Controls DEVELOPMENT/LIVE mode with Demo-Aware Auto Trading

This module implements strict mode control to ensure:
- DEVELOPMENT mode: Safe for testing, auto-trading only on DEMO accounts
- LIVE mode: Production trading with full automation on both DEMO and REAL accounts
- REAL accounts in DEVELOPMENT: Trading blocked for safety
- REAL accounts in LIVE: Requires explicit user confirmation

CRITICAL RULES:
1. Mode changes require application restart
2. Account type detection drives automation limits
3. Invalid mode/account combinations are blocked
4. No silent failures - all decisions logged
"""

import logging
from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import json
from pathlib import Path


class RuntimeMode(Enum):
    """Application runtime mode."""
    DEVELOPMENT = "DEVELOPMENT"
    LIVE = "LIVE"


class AccountType(Enum):
    """MT5 account type."""
    DEMO = "DEMO"
    REAL = "REAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class AutomationPolicy:
    """Automation policy for specific mode/account combination."""
    auto_trading: bool
    auto_startup: bool = False
    auto_restart: bool = False
    auto_reconnect: bool = True
    offline_recovery: bool = True
    watchdogs_enabled: bool = False
    confirmation_required: bool = False
    confirmation_text: Optional[str] = None
    delay_seconds: int = 0
    block_reason: Optional[str] = None


class RuntimeModeManager:
    """
    Manages runtime mode (DEVELOPMENT/LIVE) and account type (DEMO/REAL).
    
    Responsibilities:
    - Detect and validate MT5 account type
    - Enforce automation matrix rules
    - Block unsafe mode/account combinations
    - Provide UI-friendly mode information
    - Log all mode-related decisions
    """
    
    # Automation Matrix
    AUTOMATION_MATRIX = {
        RuntimeMode.DEVELOPMENT: {
            AccountType.DEMO: AutomationPolicy(
                auto_trading=True,
                auto_startup=False,
                auto_restart=False,
                auto_reconnect=True,
                offline_recovery=True,
                watchdogs_enabled=False
            ),
            AccountType.REAL: AutomationPolicy(
                auto_trading=False,
                block_reason="REAL account cannot auto-trade in DEVELOPMENT mode"
            ),
            AccountType.UNKNOWN: AutomationPolicy(
                auto_trading=False,
                block_reason="Account type unknown - cannot enable auto-trading"
            )
        },
        RuntimeMode.LIVE: {
            AccountType.DEMO: AutomationPolicy(
                auto_trading=True,
                auto_startup=True,
                auto_restart=True,
                auto_reconnect=True,
                offline_recovery=True,
                watchdogs_enabled=True
            ),
            AccountType.REAL: AutomationPolicy(
                auto_trading=True,
                auto_startup=True,
                auto_restart=True,
                auto_reconnect=True,
                offline_recovery=True,
                watchdogs_enabled=True,
                confirmation_required=True,
                confirmation_text="I CONFIRM LIVE REAL ACCOUNT AUTOTRADING",
                delay_seconds=10
            ),
            AccountType.UNKNOWN: AutomationPolicy(
                auto_trading=False,
                block_reason="Account type unknown - cannot enable auto-trading"
            )
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize Runtime Mode Manager.
        
        Args:
            config_path: Path to config.yaml (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path
        
        # Current state
        self.runtime_mode: RuntimeMode = RuntimeMode.DEVELOPMENT
        self.account_type: AccountType = AccountType.UNKNOWN
        self.current_policy: Optional[AutomationPolicy] = None
        self.confirmation_given: bool = False
        
        # Load mode from config
        self._load_runtime_mode_from_config()
        
        self.logger.info("=" * 60)
        self.logger.info("Runtime Mode Manager Initialized")
        self.logger.info(f"   Mode: {self.runtime_mode.value}")
        self.logger.info("=" * 60)
    
    def _load_runtime_mode_from_config(self):
        """Load runtime mode from config.yaml."""
        try:
            if self.config_path and self.config_path.exists():
                import yaml
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                mode_str = config.get('runtime', {}).get('mode', 'DEVELOPMENT')
                try:
                    self.runtime_mode = RuntimeMode(mode_str.upper())
                    self.logger.info(f"Loaded runtime mode from config: {self.runtime_mode.value}")
                except ValueError:
                    self.logger.warning(f"Invalid runtime mode '{mode_str}' in config, using DEVELOPMENT")
                    self.runtime_mode = RuntimeMode.DEVELOPMENT
            else:
                self.logger.info("No config file, defaulting to DEVELOPMENT mode")
                self.runtime_mode = RuntimeMode.DEVELOPMENT
        except Exception as e:
            self.logger.error(f"Error loading runtime mode from config: {e}")
            self.runtime_mode = RuntimeMode.DEVELOPMENT
    
    def detect_account_type(self, account_info: Dict) -> AccountType:
        """
        Detect MT5 account type from account info.
        
        Args:
            account_info: Dict from mt5.account_info()._asdict()
            
        Returns:
            AccountType enum
        """
        try:
            if not account_info:
                self.logger.error("No account info provided")
                return AccountType.UNKNOWN
            
            # Check trade_mode field (most reliable)
            # ACCOUNT_TRADE_MODE_DEMO = 0
            # ACCOUNT_TRADE_MODE_CONTEST = 1
            # ACCOUNT_TRADE_MODE_REAL = 2
            trade_mode = account_info.get('trade_mode', -1)
            
            if trade_mode == 0 or trade_mode == 1:  # DEMO or CONTEST
                account_type = AccountType.DEMO
            elif trade_mode == 2:  # REAL
                account_type = AccountType.REAL
            else:
                # Fallback: check server name and account details
                server = account_info.get('server', '').lower()
                name = account_info.get('name', '').lower()
                company = account_info.get('company', '').lower()
                
                # Check for demo indicators in server/name/company
                if any(keyword in text for keyword in ['demo', 'contest', 'test'] 
                      for text in [server, name, company]):
                    account_type = AccountType.DEMO
                    self.logger.info(f"Detected DEMO from metadata (server={server}, name={name})")
                else:
                    # If unsure, treat as REAL for safety
                    account_type = AccountType.REAL
                    self.logger.warning(f"Could not determine account type from trade_mode={trade_mode}, assuming REAL for safety")
                    self.logger.warning(f"   Server: {server}, Name: {name}, Company: {company}")
            
            self.account_type = account_type
            
            self.logger.info("=" * 60)
            self.logger.info("MT5 Account Type Detection")
            self.logger.info(f"   Trade Mode: {trade_mode}")
            self.logger.info(f"   Server: {account_info.get('server', 'N/A')}")
            self.logger.info(f"   Account: {account_info.get('login', 'N/A')}")
            self.logger.info(f"   Name: {account_info.get('name', 'N/A')}")
            self.logger.info(f"   Company: {account_info.get('company', 'N/A')}")
            self.logger.info(f"   Detected Type: {account_type.value}")
            self.logger.info("=" * 60)
            
            return account_type
            
        except Exception as e:
            self.logger.error(f"Error detecting account type: {e}", exc_info=True)
            self.account_type = AccountType.UNKNOWN
            return AccountType.UNKNOWN
    
    def validate_and_get_policy(self) -> Tuple[bool, AutomationPolicy, str]:
        """
        Validate current mode/account combination and get automation policy.
        
        Returns:
            Tuple of (is_valid, policy, message)
        """
        try:
            # Get policy from matrix
            policy = self.AUTOMATION_MATRIX[self.runtime_mode][self.account_type]
            self.current_policy = policy
            
            # Check if combination is blocked
            if policy.block_reason:
                msg = (f"BLOCKED: {policy.block_reason}\n"
                    f"   Mode: {self.runtime_mode.value}\n"
                    f"   Account: {self.account_type.value}")
                self.logger.error(msg)
                return False, policy, msg
            
            # Build status message
            msg_lines = [
                "=" * 60,
                "Runtime Mode Validation",
                f"   Mode: {self.runtime_mode.value}",
                f"   Account: {self.account_type.value}",
                f"   Auto Trading: {'ENABLED' if policy.auto_trading else 'DISABLED'}",
            ]
            
            if policy.auto_trading:
                msg_lines.extend([
                    f"   Auto Startup: {'Yes' if policy.auto_startup else 'No'}",
                    f"   Auto Restart: {'Yes' if policy.auto_restart else 'No'}",
                    f"   Auto Reconnect: {'Yes' if policy.auto_reconnect else 'No'}",
                    f"   Offline Recovery: {'Yes' if policy.offline_recovery else 'No'}",
                    f"   Watchdogs: {'Yes' if policy.watchdogs_enabled else 'No'}",
                ])
                
                if policy.confirmation_required:
                    msg_lines.append(f"   Confirmation Required: Yes (delay: {policy.delay_seconds}s)")
            
            msg_lines.append("=" * 60)
            msg = "\n".join(msg_lines)
            
            self.logger.info(msg)
            return True, policy, msg
            
        except Exception as e:
            msg = f"Error validating mode/account: {e}"
            self.logger.error(msg, exc_info=True)
            return False, AutomationPolicy(auto_trading=False, block_reason=str(e)), msg
    
    def request_confirmation(self) -> bool:
        """
        Request user confirmation for REAL account auto-trading in LIVE mode.
        
        Returns:
            True if confirmation given, False otherwise
        """
        if not self.current_policy or not self.current_policy.confirmation_required:
            return True  # No confirmation needed
        
        if self.confirmation_given:
            return True  # Already confirmed
        
        self.logger.warning("=" * 60)
        self.logger.warning("REAL ACCOUNT AUTO-TRADING CONFIRMATION REQUIRED")
        self.logger.warning(f"   Mode: {self.runtime_mode.value}")
        self.logger.warning(f"   Account: {self.account_type.value}")
        self.logger.warning(f"   Required Text: {self.current_policy.confirmation_text}")
        self.logger.warning(f"   Delay: {self.current_policy.delay_seconds} seconds")
        self.logger.warning("=" * 60)
        
        # In GUI application, this should trigger a dialog
        # For now, return False to prevent auto-trading without explicit confirmation
        return False
    
    def set_confirmation(self, confirmed: bool):
        """Set confirmation status for REAL account auto-trading."""
        self.confirmation_given = confirmed
        if confirmed:
            self.logger.info("REAL account auto-trading confirmation given")
        else:
            self.logger.warning("REAL account auto-trading confirmation denied")
    
    def can_auto_trade(self) -> Tuple[bool, str]:
        """
        Check if auto-trading is allowed in current mode/account combination.
        
        Returns:
            Tuple of (allowed, reason)
        """
        if not self.current_policy:
            return False, "Policy not initialized"
        
        if not self.current_policy.auto_trading:
            reason = self.current_policy.block_reason or "Auto-trading not allowed in this mode/account combination"
            return False, reason
        
        if self.current_policy.confirmation_required and not self.confirmation_given:
            return False, "Confirmation required for REAL account auto-trading"
        
        return True, "Auto-trading allowed"
    
    def get_mode_display_text(self) -> str:
        """Get display text for current mode (for UI)."""
        if self.runtime_mode == RuntimeMode.DEVELOPMENT:
            return "Development"
        else:
            return "Live Trading"
    
    def get_account_display_text(self) -> str:
        """Get display text for account type (for UI)."""
        if self.account_type == AccountType.DEMO:
            return "Demo Account"
        elif self.account_type == AccountType.REAL:
            return "Real Account"
        else:
            return "Unknown Account"
    
    def get_status_color(self) -> str:
        """Get status color for UI (green/yellow/red)."""
        if not self.current_policy:
            return "red"
        
        if self.current_policy.auto_trading:
            if self.account_type == AccountType.REAL:
                return "yellow"  # REAL account - caution
            else:
                return "green"  # DEMO account - safe
        else:
            return "red"  # Auto-trading blocked
    
    def save_mode_to_config(self, new_mode: RuntimeMode) -> bool:
        """
        Save runtime mode to config.yaml.
        
        Args:
            new_mode: New runtime mode
            
        Returns:
            True if saved successfully
        """
        try:
            if not self.config_path:
                self.logger.error("No config path provided")
                return False
            
            import yaml
            
            # Load existing config
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Update runtime mode
            if 'runtime' not in config:
                config['runtime'] = {}
            config['runtime']['mode'] = new_mode.value
            
            # Save config
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            
            self.logger.info(f"Saved runtime mode to config: {new_mode.value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving runtime mode to config: {e}", exc_info=True)
            return False


# Singleton instance
_runtime_manager_instance: Optional[RuntimeModeManager] = None


def get_runtime_manager(config_path: Optional[Path] = None) -> RuntimeModeManager:
    """Get singleton RuntimeModeManager instance."""
    global _runtime_manager_instance
    if _runtime_manager_instance is None:
        _runtime_manager_instance = RuntimeModeManager(config_path)
    return _runtime_manager_instance
