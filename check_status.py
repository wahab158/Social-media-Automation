import os
import json
from db_helper import DBHelper
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

def check_status_counts():
    try:
        db = DBHelper()
        db.connect()
        
        records = db.content_sheet.get_all_records()
        statuses = [r.get('status') for r in records]
        counts = Counter(statuses)
        print("\nStatus counts in Content Queue:")
        for status, count in counts.items():
            print(f"- {status}: {count}")
            
        print("\nRecent 'Draft' items (if any):")
        recent_drafts = [r for r in records if r.get('status') == 'Draft'][-5:]
        for d in recent_drafts:
            print(f"- Topic: {d.get('topic')}, Created: {d.get('posted_at') or 'Unknown'}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_status_counts()
