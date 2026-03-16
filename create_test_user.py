import sqlite3
import uuid
from datetime import datetime
from bcrypt import hashpw, gensalt
import os

DB_PATH = "autopost.db"

def create_temp_user():
    conn = sqlite3.connect(DB_PATH)
    email = "tester@example.com"
    password = "password"
    hashed = hashpw(password.encode('utf-8'), gensalt()).decode('utf-8')
    uid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    try:
        conn.execute(
            "INSERT INTO users (id, email, password, name, created_at) VALUES (?, ?, ?, ?, ?)",
            (uid, email, hashed, "Tester", now)
        )
        conn.commit()
        print(f"User {email} created successfully.")
    except sqlite3.IntegrityError:
        print(f"User {email} already exists.")
    finally:
        conn.close()

if __name__ == "__main__":
    create_temp_user()
