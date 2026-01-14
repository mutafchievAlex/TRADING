# TEMP FIX FILE - Just the corrected method section
# Lines 333-349 of recovery_engine.py should be:

            # Check 2: Take Profit hit
            if current_close >= take_profit:
                return {
                    'should_close': True,
                    'reason': f'Take Profit hit at {current_close:.2f} (TP: {take_profit:.2f})',
                    'exit_price': take_profit
                }
            
            # Pattern validity is NOT an exit condition after entry
            # Before TP1: Only SL hits can close positions
            # Pattern engine is entry-only, not exit logic
            
            # Position should remain open
            return {
                'should_close': False,
                'reason': f'Position valid: SL={stop_loss:.2f}, TP={take_profit:.2f}, Current={current_close:.2f}'
            }
