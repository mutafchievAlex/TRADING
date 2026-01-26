#!/usr/bin/env python3
"""Show actual exit reasons in database."""

import sqlite3

conn = sqlite3.connect('data/state.db')
cursor = conn.cursor()

print('\n' + '='*90)
print('ACTUAL EXIT REASONS IN DATABASE')
print('='*90 + '\n')

cursor.execute('SELECT DISTINCT exit_reason FROM trades ORDER BY exit_reason')
reasons = cursor.fetchall()

print('Exit reason types currently in database:\n')
for reason_tuple in reasons:
    reason = reason_tuple[0]
    cursor.execute('SELECT COUNT(*) FROM trades WHERE exit_reason = ?', (reason,))
    count = cursor.fetchone()[0]
    print(f'  • "{reason}" ({count} trades)')

print('\n' + '='*90)
print('EXAMPLES OF EACH TYPE')
print('='*90 + '\n')

cursor.execute('SELECT DISTINCT exit_reason FROM trades')
for reason_tuple in cursor.fetchall():
    reason = reason_tuple[0]
    cursor.execute('''
        SELECT ticket, entry_time, exit_time, entry_price, exit_price, profit
        FROM trades
        WHERE exit_reason = ?
        LIMIT 1
    ''', (reason,))
    
    result = cursor.fetchone()
    if result:
        ticket, entry, exit_t, entry_p, exit_p, profit = result
        profit_icon = '✅' if profit > 0 else '❌'
        print(f'Reason: "{reason}"')
        print(f'  Example: Ticket {ticket}')
        print(f'  Entry:   {entry} @ {entry_p:.2f}')
        print(f'  Exit:    {exit_t} @ {exit_p:.2f}')
        print(f'  {profit_icon} P&L: ${profit:.2f}\n')

conn.close()
