"""
Multi-Level TP Engine - Practical Examples

This file demonstrates the multi-level TP system in action
with real trading scenarios.
"""

from src.engines.multi_level_tp_engine import MultiLevelTPEngine, TPState


def example_1_tp_level_calculation():
    """
    Example 1: Calculate TP levels for a LONG trade
    
    Scenario: Gold (XAUUSD) breakout
    - Entry: 2000.00
    - Stop Loss: 1990.00 (10 pips below entry)
    - Direction: LONG (+1)
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: TP Level Calculation")
    print("="*60)
    
    engine = MultiLevelTPEngine(default_rr_long=2.0, default_rr_short=2.0)
    
    tp_levels = engine.calculate_tp_levels(
        entry_price=2000.00,
        stop_loss=1990.00,
        direction=1  # LONG
    )
    
    print(f"\nEntry: 2000.00")
    print(f"Stop Loss: 1990.00")
    print(f"Risk per unit: {tp_levels['risk']:.2f} pips")
    print(f"\nTP Levels:")
    print(f"  TP1 (1.4x RR): {tp_levels['tp1']:.2f}")
    print(f"  TP2 (1.8x RR): {tp_levels['tp2']:.2f}")
    print(f"  TP3 (2.0x RR): {tp_levels['tp3']:.2f}")
    
    return tp_levels


def example_2_state_machine_success():
    """
    Example 2: Successful trade progression through all TP levels
    
    Price progression:
    2000.00 (entry) -> 2014.00 (TP1) -> 2018.00 (TP2) -> 2020.00 (TP3)
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Successful Trade Progression (TP1 → TP2 → TP3)")
    print("="*60)
    
    engine = MultiLevelTPEngine(default_rr_long=2.0)
    
    entry_price = 2000.00
    stop_loss = 1990.00
    tp_levels = engine.calculate_tp_levels(entry_price, stop_loss, direction=1)
    
    print(f"\nInitial setup:")
    print(f"  Entry: {entry_price:.2f}")
    print(f"  SL: {stop_loss:.2f}")
    print(f"  TP1: {tp_levels['tp1']:.2f}")
    print(f"  TP2: {tp_levels['tp2']:.2f}")
    print(f"  TP3: {tp_levels['tp3']:.2f}")
    
    # Simulate price progression
    prices = [
        (2010.00, "Approaching TP1"),
        (2014.00, "REACHES TP1"),
        (2015.00, "Between TP1 and TP2"),
        (2018.00, "REACHES TP2"),
        (2019.00, "Between TP2 and TP3"),
        (2020.00, "REACHES TP3 (Full Exit)"),
    ]
    
    tp_state = TPState.IN_TRADE.value
    current_sl = stop_loss
    
    print(f"\nPrice progression:")
    for price, description in prices:
        should_exit, reason, new_state = engine.evaluate_exit(
            current_price=price,
            entry_price=entry_price,
            stop_loss=current_sl,
            tp_state=tp_state,
            tp_levels=tp_levels,
            direction=1
        )
        
        if new_state != tp_state:
            print(f"\n  {price:.2f}: {description}")
            print(f"    State: {tp_state} → {new_state}")
            print(f"    SL: {current_sl:.2f}")
            
            # Calculate new SL if state changed to TP1 or TP2
            if new_state in [TPState.TP1_REACHED.value, TPState.TP2_REACHED.value]:
                new_sl = engine.calculate_new_stop_loss(
                    current_price=price,
                    entry_price=entry_price,
                    tp_state=new_state,
                    direction=1,
                    trailing_offset=0.5
                )
                if new_sl:
                    current_sl = new_sl
                    print(f"    New SL: {current_sl:.2f}")
            
            tp_state = new_state
        else:
            print(f"\n  {price:.2f}: {description} (no state change)")


def example_3_failed_continuation():
    """
    Example 3: Trade reversal after TP1
    
    Price progression:
    2000.00 (entry) -> 2014.00 (TP1, SL moves to 2000.00)
    -> 2015.00 -> 1999.50 (REVERSAL - SL HIT)
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Failed Continuation After TP1")
    print("="*60)
    
    engine = MultiLevelTPEngine(default_rr_long=2.0)
    
    entry_price = 2000.00
    stop_loss = 1990.00
    tp_levels = engine.calculate_tp_levels(entry_price, stop_loss, direction=1)
    
    print(f"\nInitial setup:")
    print(f"  Entry: {entry_price:.2f}")
    print(f"  SL: {stop_loss:.2f}")
    print(f"  TP1: {tp_levels['tp1']:.2f}")
    
    # Price moves to TP1
    print(f"\n[1] Price reaches TP1 (2014.00)")
    should_exit, reason, new_state = engine.evaluate_exit(
        current_price=2014.00,
        entry_price=entry_price,
        stop_loss=stop_loss,
        tp_state=TPState.IN_TRADE.value,
        tp_levels=tp_levels,
        direction=1
    )
    
    new_sl = engine.calculate_new_stop_loss(
        current_price=2014.00,
        entry_price=entry_price,
        tp_state=new_state,
        direction=1,
        trailing_offset=0.5
    )
    current_sl = new_sl if new_sl else stop_loss
    current_state = new_state
    
    print(f"    Action: SL moved to {current_sl:.2f} (entry price = breakeven)")
    print(f"    State: {TPState.IN_TRADE.value} → {current_state}")
    
    # Price tries to extend to TP2
    print(f"\n[2] Price reaches 2015.00")
    print(f"    Action: Continue toward TP2")
    
    # But then reverses
    print(f"\n[3] Price reverses to 1999.50 (below new SL)")
    should_exit, reason, new_state = engine.evaluate_exit(
        current_price=1999.50,
        entry_price=entry_price,
        stop_loss=current_sl,
        tp_state=current_state,
        tp_levels=tp_levels,
        direction=1
    )
    
    print(f"    Current SL: {current_sl:.2f}")
    print(f"    Price: 1999.50")
    print(f"    Result: STOP LOSS HIT!")
    print(f"    Reason: {reason}")
    print(f"    Profit: ~0 (SL was at entry price = breakeven protection)")


def example_4_trailing_stop():
    """
    Example 4: Trailing stop after TP2
    
    Price progression:
    2000.00 -> 2014.00 (TP1, SL→2000) -> 2018.00 (TP2, SL trails)
    -> 2025.00 (new high) -> 2024.50 (SL trails to 2024.50)
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Trailing Stop After TP2")
    print("="*60)
    
    engine = MultiLevelTPEngine(default_rr_long=2.0)
    
    entry_price = 2000.00
    stop_loss = 1990.00
    tp_levels = engine.calculate_tp_levels(entry_price, stop_loss, direction=1)
    
    print(f"\nInitial setup:")
    print(f"  Entry: {entry_price:.2f}")
    print(f"  TP2: {tp_levels['tp2']:.2f}")
    
    # Progression to TP2
    tp_state = TPState.TP1_REACHED.value
    current_sl = entry_price  # SL at entry from TP1
    
    print(f"\n[1] Price reaches 2018.00 (TP2)")
    should_exit, reason, new_state = engine.evaluate_exit(
        current_price=2018.00,
        entry_price=entry_price,
        stop_loss=current_sl,
        tp_state=tp_state,
        tp_levels=tp_levels,
        direction=1
    )
    
    new_sl = engine.calculate_new_stop_loss(
        current_price=2018.00,
        entry_price=entry_price,
        tp_state=new_state,
        direction=1,
        trailing_offset=0.5
    )
    current_sl = new_sl if new_sl else current_sl
    tp_state = new_state
    print(f"    State: {TPState.TP1_REACHED.value} → {new_state}")
    print(f"    SL moves to: {current_sl:.2f} (trailing mode active)")
    
    # Price continues higher
    print(f"\n[2] Price rallies to 2025.00 (beyond TP3)")
    print(f"    Current SL: {current_sl:.2f}")
    
    # Calculate new trailing SL at this price
    new_trailing_sl = engine.calculate_new_stop_loss(
        current_price=2025.00,
        entry_price=entry_price,
        tp_state=TPState.TP2_REACHED.value,
        direction=1,
        trailing_offset=0.5
    )
    
    print(f"    SL updates to: {new_trailing_sl:.2f} (price - 0.5 pips)")
    
    # If price drops
    print(f"\n[3] Price drops to 2024.50 (hits trailing SL)")
    print(f"    Current SL: {new_trailing_sl:.2f}")
    print(f"    Price: 2024.50")
    print(f"    Result: STOP LOSS HIT (trailing stop captured extra profit)")


def example_5_next_target():
    """
    Example 5: Display next target based on current TP state
    """
    print("\n" + "="*60)
    print("EXAMPLE 5: Next Target Display (for UI)")
    print("="*60)
    
    engine = MultiLevelTPEngine(default_rr_long=2.0)
    
    tp_levels = {
        'tp1': 2014.00,
        'tp2': 2018.00,
        'tp3': 2020.00,
    }
    
    states = [
        TPState.IN_TRADE.value,
        TPState.TP1_REACHED.value,
        TPState.TP2_REACHED.value,
    ]
    
    print(f"\nTP Levels: TP1=2014, TP2=2018, TP3=2020")
    print(f"\nNext targets by state:")
    
    for state in states:
        next_target = engine.get_next_target(state, tp_levels)
        print(f"  State {state:20s} → Next target: {next_target:.2f}")


if __name__ == "__main__":
    # Run all examples
    example_1_tp_level_calculation()
    example_2_state_machine_success()
    example_3_failed_continuation()
    example_4_trailing_stop()
    example_5_next_target()
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
