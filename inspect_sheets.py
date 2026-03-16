import os
import json
from db_helper import DBHelper
from dotenv import load_dotenv

load_dotenv()

def check_sheets():
    try:
        db = DBHelper()
        db.connect()
        
        print("\n--- Content Queue ---")
        headers = db.content_sheet.row_values(1)
        print(f"Headers: {headers}")
        
        records = db.content_sheet.get_all_records()
        print(f"Total records in Content Queue: {len(records)}")
        if records:
            print("First record keys:", records[0].keys())
            print("First record values:", records[0])
            
        print("\n--- News Database ---")
        headers_news = db.news_sheet.row_values(1)
        print(f"Headers: {headers_news}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_sheets()
