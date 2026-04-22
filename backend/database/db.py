import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = "ojamoni.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS traders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            business_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trader_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            revenue REAL DEFAULT 0,
            expenses REAL DEFAULT 0,
            profit REAL DEFAULT 0,
            raw_input TEXT,
            ai_insight TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trader_id) REFERENCES traders(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trader_id INTEGER NOT NULL,
            sender TEXT NOT NULL DEFAULT 'trader',
            message TEXT NOT NULL,
            sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (trader_id) REFERENCES traders(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized")

def save_trader(name, phone, business_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO traders (name, phone, business_type)
        VALUES (?, ?, ?)
    """, (name, phone, business_type))
    conn.commit()
    trader_id = cursor.lastrowid
    conn.close()
    return trader_id

def get_trader_by_phone(phone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traders WHERE phone = ?", (phone,))
    trader = cursor.fetchone()
    conn.close()
    return trader

def get_all_traders():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM traders")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_transaction(trader_id, date, revenue, expenses, profit, raw_input, ai_insight):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (trader_id, date, revenue, expenses, profit, raw_input, ai_insight)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (trader_id, date, revenue, expenses, profit, raw_input, ai_insight))
    conn.commit()
    conn.close()

def get_recent_transactions(trader_id, days=7):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM transactions
        WHERE trader_id = ?
        ORDER BY date DESC
        LIMIT ?
    """, (trader_id, days))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_last_transaction_date(trader_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT MAX(date) as last_date FROM transactions
        WHERE trader_id = ?
    """, (trader_id,))
    row = cursor.fetchone()
    conn.close()
    return row["last_date"] if row else None

def log_message(trader_id, message, sender="trader"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages_log (trader_id, message, sender)
        VALUES (?, ?, ?)
    """, (trader_id, message, sender))
    conn.commit()
    conn.close()

def get_messages_log(trader_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM messages_log
        WHERE trader_id = ?
        ORDER BY sent_at ASC
    """, (trader_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]