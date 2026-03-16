import sqlite3
import os

DB_PATH = "autopost.db"

def update_schedule(new_time):
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE user_settings SET post_time = ?", (new_time,))
        conn.commit()
        print(f"Updated {cursor.rowcount} rows to {new_time}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_schedule("11:45")
