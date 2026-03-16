import os
import json
from db_helper import DBHelper
from dotenv import load_dotenv

load_dotenv()

def check_last_items():
    try:
        db = DBHelper()
        db.connect()
        
        all_values = db.content_sheet.get_all_values()
        print(f"Total rows in Content Queue (including headers): {len(all_values)}")
        
        headers = all_values[0]
        last_rows = all_values[-10:]
        
        print("\nLast 10 rows:")
        for i, row in enumerate(last_rows):
            # Calculate physical row index
            phys_idx = len(all_values) - 10 + i + 1
            # status is at index 8
            status = row[8] if len(row) > 8 else "N/A"
            topic = row[0] if len(row) > 0 else "N/A"
            print(f"Row {phys_idx} | Status: {status} | Topic: {topic[:50]}...")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_last_items()
