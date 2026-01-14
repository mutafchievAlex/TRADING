"""
Setup Verification Script

Run this script to verify that all components are properly installed
and configured before starting the trading application.
"""

import sys
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.10 or higher."""
    print("Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        print(f"  [OK] Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  [X] Python {version.major}.{version.minor}.{version.micro} - Need 3.10+")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\nChecking dependencies...")
    
    required = {
        'MetaTrader5': 'MetaTrader5',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'yaml': 'PyYAML',
        'PySide6': 'PySide6'
    }
    
    all_ok = True
    for module, package in required.items():
        try:
            __import__(module)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [X] {package} - Not installed")
            all_ok = False
    
    return all_ok


def check_project_structure():
    """Check if project structure is complete."""
    print("\nChecking project structure...")
    
    required_dirs = [
        'src/engines',
        'src/ui',
        'src/utils',
        'config',
        'tests',
        'scripts',
        'data/historical'
    ]
    
    required_files = [
        'src/main.py',
        'src/engines/market_data_service.py',
        'src/engines/indicator_engine.py',
        'src/engines/pattern_engine.py',
        'src/engines/strategy_engine.py',
        'src/engines/risk_engine.py',
        'src/engines/execution_engine.py',
        'src/engines/state_manager.py',
        'src/ui/main_window.py',
        'src/utils/config.py',
        'src/utils/logger.py',
        'config/config.yaml',
        'requirements.txt',
        'README.md'
    ]
    
    project_root = Path(__file__).parent
    all_ok = True
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            print(f"  [OK] {dir_path}/")
        else:
            print(f"  [X] {dir_path}/ - Missing")
            all_ok = False
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  [OK] {file_path}")
        else:
            print(f"  [X] {file_path} - Missing")
            all_ok = False
    
    return all_ok


def check_mt5():
    """Check if MT5 is available, trying configured terminal_path if needed."""
    print("\nChecking MetaTrader 5 connection...")

    try:
        import os
        import MetaTrader5 as mt5

        # Try to load terminal_path from config if available
        terminal_path = None
        try:
            sys.path.insert(0, str(Path(__file__).parent / 'src'))
            from utils.config import load_config
            cfg = load_config('config/config.yaml')
            terminal_path = cfg.get('mt5.terminal_path') or os.environ.get('MT5_TERMINAL_PATH')
        except Exception:
            # Config might not be importable yet; fall back to env var
            terminal_path = os.environ.get('MT5_TERMINAL_PATH')

        initialized = False
        if terminal_path:
            initialized = mt5.initialize(path=terminal_path)
            if not initialized:
                le = mt5.last_error()
                print(f"  ✗ Initialize with terminal_path failed: {le}")
        if not initialized:
            initialized = mt5.initialize()

        if initialized:
            info = mt5.terminal_info()
            if info:
                print(f"  [OK] MT5 Terminal connected")
                print(f"    Build: {info.build}")
                print(f"    Company: {info.company}")
                print(f"    Trade allowed: {getattr(info, 'trade_allowed', None)}")

            account_info = mt5.account_info()
            if account_info:
                print(f"  [OK] Account connected")
                print(f"    Login: {account_info.login}")
                print(f"    Server: {account_info.server}")
                print(f"    Balance: ${account_info.balance:.2f}")

            mt5.shutdown()
            return True
        else:
            le = mt5.last_error()
            print("  [X] MT5 initialization failed")
            print(f"    Last error: {le}")
            print("    Hints:")
            print("      - Install MetaTrader 5 (64-bit) and log in")
            print("      - Or set mt5.terminal_path in config/config.yaml to terminal64.exe")
            print("      - Or set MT5_TERMINAL_PATH environment variable")
            return False

    except Exception as e:
        print(f"  [X] Error: {e}")
        return False


def check_configuration():
    """Check if configuration file is valid."""
    print("\nChecking configuration...")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'src'))
        from utils.config import load_config
        
        config = load_config('config/config.yaml')
        print(f"  [OK] Configuration loaded")
        print(f"    Symbol: {config.mt5_symbol}")
        print(f"    Timeframe: {config.mt5_timeframe}")
        print(f"    Demo Mode: {config.is_demo_mode}")
        print(f"    Auto Trade: {config.auto_trade_enabled}")
        print(f"    Risk %: {config.risk_percent}")
        
        return True
        
    except Exception as e:
        print(f"  [X] Configuration error: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("TRADING APPLICATION SETUP VERIFICATION")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_dependencies(),
        check_project_structure(),
        check_configuration(),
        check_mt5()
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("ALL CHECKS PASSED")
        print("=" * 60)
        print("\nYou can now run the application:")
        print("  python src/main.py")
    else:
        print("SOME CHECKS FAILED")
        print("=" * 60)
        print("\nPlease fix the issues above before running the application.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Ensure MT5 is running and logged in")
        print("  - Check config/config.yaml exists")
    
    print()


if __name__ == "__main__":
    main()
