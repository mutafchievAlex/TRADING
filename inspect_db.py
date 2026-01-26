#!/usr/bin/env python3
"""
Inspect trading database - view all tables and records.
Shows complete state from both database and JSON file.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

def format_table(title, rows, columns):
    """Pretty print a table."""
    if not rows:
        print(f"\n{title}: [EMPTY]")
        return
    
    print(f"\n{'='*120}")
    print(f"{title}")
    print('='*120)
    
    # Calculate column widths
    col_widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row.get(col, ''))
            col_widths[col] = max(col_widths[col], len(val))
    
    # Print header
    header = ' | '.join(f"{col:{col_widths[col]}}" for col in columns)
    print(header)
    print('-' * len(header))
    
    # Print rows
    for row in rows:
        row_str = ' | '.join(f"{str(row.get(col, '')):{col_widths[col]}}" for col in columns)
        print(row_str)
    
    print(f"Total: {len(rows)} records")


def main():
    db_path = Path('data/state.db')
    if not db_path.exists():
        print("❌ Database not found: data/state.db")
        return
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n" + "="*120)
    print("DATABASE INSPECTION - TRADING STATE")
    print("="*120)
    print(f"Database: {db_path.absolute()}")
    print(f"Size: {db_path.stat().st_size / 1024:.1f} KB")
    print(f"Last modified: {datetime.fromtimestamp(db_path.stat().st_mtime).isoformat()}")
    
    # Get all tables
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    
    print(f"\nTables found: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")
    
    # TRADING_STATE
    print("\n" + "="*120)
    print("1. TRADING STATE (Global metadata)")
    print("="*120)
    state = cursor.execute("SELECT * FROM trading_state LIMIT 1").fetchone()
    if state:
        print(f"  Last trade time:    {state['last_trade_time']}")
        print(f"  Total trades:       {state['total_trades']}")
        print(f"  Winning trades:     {state['winning_trades']}")
        print(f"  Losing trades:      {state['losing_trades']}")
        print(f"  Total profit:       ${state['total_profit']:.2f}")
        print(f"  Saved at:           {state['saved_at']}")
    else:
        print("  [EMPTY]")
    
    # POSITIONS
    print("\n" + "="*120)
    print("2. OPEN POSITIONS")
    print("="*120)
    positions = cursor.execute(
        "SELECT ticket, entry_time, entry_price, stop_loss, take_profit, volume, tp_state, profit FROM positions ORDER BY entry_time DESC"
    ).fetchall()
    
    if positions:
        format_table(
            "Open Positions",
            [dict(p) for p in positions],
            ['ticket', 'entry_time', 'entry_price', 'stop_loss', 'take_profit', 'volume', 'tp_state', 'profit']
        )
    else:
        print("  [NO OPEN POSITIONS]")
    
    # TRADES
    print("\n" + "="*120)
    print("3. TRADE HISTORY (Last 20)")
    print("="*120)
    trades = cursor.execute(
        """
        SELECT id, ticket, entry_time, exit_time, entry_price, exit_price, 
               volume, profit, net_pl, exit_reason, is_winner
        FROM trades
        ORDER BY id DESC
        LIMIT 20
        """
    ).fetchall()
    
    if trades:
        # Format trades for display with exit reason
        trades_display = []
        for t in trades:
            trade_dict = dict(t)
            trade_dict['reason'] = trade_dict.get('exit_reason', 'Unknown')
            trades_display.append(trade_dict)
        
        format_table(
            "Last 20 Completed Trades",
            trades_display,
            ['id', 'ticket', 'entry_time', 'exit_time', 'entry_price', 'exit_price', 'volume', 'profit', 'reason']
        )
    else:
        print("  [NO TRADES IN HISTORY]")
    
    # SNAPSHOTS
    print("\n" + "="*120)
    print("4. STATE SNAPSHOTS (Last 5)")
    print("="*120)
    snapshots = cursor.execute(
        "SELECT id, created_at FROM state_snapshots ORDER BY id DESC LIMIT 5"
    ).fetchall()
    
    if snapshots:
        print(f"Total snapshots: {cursor.execute('SELECT COUNT(*) FROM state_snapshots').fetchone()[0]}")
        for snap in snapshots:
            print(f"  Snapshot #{snap['id']}: {snap['created_at']}")
    else:
        print("  [NO SNAPSHOTS]")
    
    conn.close()
    
    # Compare with JSON
    print("\n" + "="*120)
    print("5. JSON FILE STATE")
    print("="*120)
    
    json_path = Path('data/state.json')
    if json_path.exists():
        with open(json_path) as f:
            json_data = json.load(f)
        
        print(f"JSON file size: {json_path.stat().st_size / 1024:.1f} KB")
        print(f"Last modified: {datetime.fromtimestamp(json_path.stat().st_mtime).isoformat()}")
        print(f"\nJSON data:")
        print(f"  Open positions:     {len(json_data.get('open_positions', []))}")
        print(f"  Trade history:      {len(json_data.get('trade_history', []))}")
        print(f"  Last trade time:    {json_data.get('last_trade_time', 'NONE')}")
        print(f"  Total trades:       {json_data.get('total_trades', 0)}")
        print(f"  Total profit:       ${json_data.get('total_profit', 0):.2f}")
    else:
        print("  ❌ JSON file not found!")
    
    # Summary
    print("\n" + "="*120)
    print("SUMMARY")
    print("="*120)
    print(f"✅ Database has {len(positions)} open positions")
    print(f"✅ Database has {len(trades)} completed trades (showing last 20)")
    print(f"✅ Total snapshots for recovery: {len(snapshots)}")
    
    if json_path.exists():
        json_trades = len(json_data.get('trade_history', []))
        
        print(f"\n📊 Data consistency:")
        print(f"  DB trades:  {len(trades)}")
        print(f"  JSON trades: {json_trades}")
        if len(trades) == json_trades:
            print(f"  ✅ CONSISTENT")
        else:
            print(f"  ⚠️  MISMATCH - Run recover_history.py to sync")


if __name__ == '__main__':
    main()
