#!/usr/bin/env python3
"""
Simple web-based SQLite database viewer for trading data.
Access at: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
DB_PATH = "data/state.db"


def get_db_connection():
    """Create database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """Main dashboard."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get statistics
        cursor.execute('SELECT COUNT(*) as count FROM positions')
        open_pos = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM trades')
        closed_trades = cursor.fetchone()['count']
        
        cursor.execute('SELECT SUM(profit) as total FROM trades')
        total_profit = cursor.fetchone()['total'] or 0
        
        cursor.execute('SELECT COUNT(*) as wins FROM trades WHERE is_winner = 1')
        wins = cursor.fetchone()['wins']
        
        cursor.execute('SELECT COUNT(*) as losses FROM trades WHERE is_winner = 0')
        losses = cursor.fetchone()['losses']
        
        conn.close()
        
        return render_template('index.html', 
                             open_positions=open_pos,
                             closed_trades=closed_trades,
                             total_profit=total_profit,
                             wins=wins,
                             losses=losses)
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/api/positions')
def api_positions():
    """Get open positions."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ticket, entry_time, entry_price, stop_loss, take_profit, 
                   volume, tp_state, profit, current_stop_loss
            FROM positions
            ORDER BY entry_time DESC
        ''')
        positions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(positions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trades')
def api_trades():
    """Get completed trades."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        limit = request.args.get('limit', 50, type=int)
        cursor.execute('''
            SELECT id, ticket, entry_time, exit_time, entry_price, exit_price,
                   volume, profit, exit_reason, is_winner
            FROM trades
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(trades)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/exit-reasons')
def api_exit_reasons():
    """Get exit reason statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT exit_reason, COUNT(*) as count, AVG(profit) as avg_profit
            FROM trades
            GROUP BY exit_reason
            ORDER BY count DESC
        ''')
        reasons = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(reasons)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/statistics')
def api_statistics():
    """Get detailed statistics."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get trading statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN is_winner = 1 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN is_winner = 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(profit) as total_profit,
                AVG(profit) as avg_profit,
                MAX(profit) as best_trade,
                MIN(profit) as worst_trade
            FROM trades
        ''')
        stats = dict(cursor.fetchone())
        
        conn.close()
        
        # Calculate win rate
        total = stats['total_trades'] or 0
        wins = stats['winning_trades'] or 0
        win_rate = (wins / total * 100) if total > 0 else 0
        
        stats['win_rate'] = round(win_rate, 2)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search')
def api_search():
    """Search trades by ticket or exit reason."""
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify([])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Search by ticket or exit reason
        cursor.execute('''
            SELECT id, ticket, entry_time, exit_time, entry_price, exit_price,
                   profit, exit_reason
            FROM trades
            WHERE ticket LIKE ? OR exit_reason LIKE ?
            LIMIT 20
        ''', (f'%{query}%', f'%{query}%'))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Trading Database Web UI")
    print("="*60)
    print("\n📊 Open your browser and go to: http://localhost:5000")
    print("\n✅ Features:")
    print("  • View open positions")
    print("  • View completed trades")
    print("  • Exit reason statistics")
    print("  • Trading statistics")
    print("  • Search trades by ticket")
    print("\nPress CTRL+C to stop the server\n")
    
    app.run(debug=False, host='localhost', port=5000)
