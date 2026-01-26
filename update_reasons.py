#!/usr/bin/env python3
"""Update exit reasons in trades table."""

import sqlite3

db_path = 'data/state.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('UPDATE trades SET exit_reason = ? WHERE exit_reason = ?', ('CLOSED (Historical)', 'CLOSED'))
conn.commit()

count = cursor.rowcount
print(f'Updated {count} trades with new exit reason')

conn.close()
