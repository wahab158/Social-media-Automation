import sqlite3
import os

DB_PATH = "autopost.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE user_settings ADD COLUMN is_enabled INTEGER DEFAULT 1")
        conn.commit()
        print("Migrated successfully: added is_enabled to user_settings")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column is_enabled already exists.")
        else:
            print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
