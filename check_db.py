import sqlite3
import os

DB_PATH = "autopost.db"
if not os.path.exists(DB_PATH):
    print(f"Database {DB_PATH} does not exist in {os.getcwd()}")
    exit()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
try:
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    print("Tables:", [t["name"] for t in tables])
    
    if "users" in [t["name"] for t in tables]:
        users = conn.execute("SELECT email FROM users LIMIT 5").fetchall()
        print("Users:", [u["email"] for u in users])
    else:
        print("Table 'users' NOT FOUND.")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
