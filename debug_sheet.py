from db_helper import DBHelper
import json

def debug_sheet():
    db = DBHelper()
    db.connect()
    records = db.content_sheet.get_all_records()
    print(f"Total records: {len(records)}")
    last_5 = records[-5:]
    for i, r in enumerate(last_5):
        print(f"Row {len(records) - 4 + i + 1}: {r}")

if __name__ == "__main__":
    debug_sheet()
