import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# Define the scopes required for Google Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class DBHelper:
    def __init__(self, sheet_url=None, credentials_path=None):
        self.sheet_url = sheet_url or os.getenv('GOOGLE_SHEET_URL')
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        self.client = None
        self.db = None
        self.news_sheet = None
        self.content_sheet = None

    def connect(self):
        """Connects to Google Sheets using service account credentials."""
        print("DBHelper: Checking credentials path...")
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
        
        print("DBHelper: Checking sheet_url...")
        if not self.sheet_url or self.sheet_url == "https://docs.google.com/spreadsheets/d/your-sheet-id/edit":
            raise ValueError("GOOGLE_SHEET_URL is not set or is still the default example.")

        print("DBHelper: Loading service account credentials...")
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
        print("DBHelper: Authorizing gspread client...")
        self.client = gspread.authorize(creds)
        print("DBHelper: Opening sheet by URL...")
        self.db = self.client.open_by_url(self.sheet_url)
        
        print("DBHelper: Ensuring News Database exists...")
        # Ensure sheets exist
        try:
            self.news_sheet = self.db.worksheet("News Database")
            print("DBHelper: News Database found.")
            
            # Migration check: Ensure the new columns exist
            headers = self.news_sheet.row_values(1)
            if "news_id" not in headers:
                print("DBHelper: Migrating News Database to include news_id and source_name...")
                # In a real heavy DB we'd migrate existing rows, but we will just add the headers for now
                # We can append the new columns to the header row
                self.news_sheet.update_cell(1, len(headers) + 1, "news_id")
                self.news_sheet.update_cell(1, len(headers) + 2, "source_name")
                self.news_sheet.update_cell(1, len(headers) + 3, "relevance_score")
                self.news_sheet.update_cell(1, len(headers) + 4, "media_url")
        except gspread.WorksheetNotFound:
            print("DBHelper: Creating News Database...")
            self.news_sheet = self.db.add_worksheet(title="News Database", rows="1000", cols="20")
            # Setup headers
            self.news_sheet.append_row(["title", "summary", "category", "source_url", "date_found", "status", "news_id", "source_name", "relevance_score", "media_url"])

        print("DBHelper: Ensuring Content Queue exists...")
        try:
            self.content_sheet = self.db.worksheet("Content Queue")
            print("DBHelper: Content Queue found.")
            headers = self.content_sheet.row_values(1)
            if "user_id" not in headers:
                print("DBHelper: Migrating Content Queue to include user_id...")
                self.content_sheet.update_cell(1, len(headers) + 1, "user_id")
        except gspread.WorksheetNotFound:
            print("DBHelper: Creating Content Queue...")
            self.content_sheet = self.db.add_worksheet(title="Content Queue", rows="1000", cols="20")
            # Setup headers
            headers = ["topic", "reel_url", "ig_caption", "fb_caption", "li_caption", "x_caption", "platforms", 
                       "schedule_time", "status", "ig_post_url", "fb_post_url", "li_post_url", "x_post_url", "posted_at", "user_id"]
            self.content_sheet.append_row(headers)
        
        print("DBHelper: Connect complete.")

    # --- News Database Methods ---

    def add_news_row(self, title, summary, category, source_url, date_found, status="New", source_name="", relevance_score=""):
        """Adds a new row to the News Database. Avoids duplicates by checking source_url."""
        import uuid
        import hashlib
        
        if self.db is None:
            self.connect()
            
        # Robust URL Duplicate Check (Check exact URL and hash-based check to prevent query string variants if needed)
        urls = self.news_sheet.col_values(4) 
        if source_url in urls:
            return False # Duplicate found
            
        # Optional: check if title is highly identical
        titles = self.news_sheet.col_values(1)
        if title in titles:
            return False
            
        news_id = str(uuid.uuid4())
        row = [title, summary, category, source_url, str(date_found), status, news_id, source_name, str(relevance_score)]
        self.news_sheet.append_row(row)
        return True

    def get_all_news(self):
        """Returns all news rows."""
        if self.db is None:
            self.connect()
        
        records = self.news_sheet.get_all_records()
        for i, r in enumerate(records):
            r['_row_index'] = i + 2 
            # ensure news_id exists just in case it's an old row
            if 'news_id' not in r or not r['news_id']:
                r['news_id'] = f"legacy-{i+2}"
        return records

    def get_pending_news(self):
        """Returns all news rows with status 'New'."""
        all_news = self.get_all_news()
        return [r for r in all_news if r.get('status') == 'New']

    def get_news_by_id(self, news_id):
        all_news = self.get_all_news()
        for r in all_news:
            if str(r.get('news_id')) == str(news_id):
                return r
        return None
        
    def update_news_status(self, row_index, new_status):
        """Updates the status of a news item after it has been used."""
        if self.db is None:
            self.connect()
            
        # status is the 6th column
        self.news_sheet.update_cell(row_index, 6, new_status) 
        return True

    def update_news_status_by_id(self, news_id, new_status):
        """Updates the status of a news item by its UUID."""
        news_item = self.get_news_by_id(news_id)
        if news_item:
            self.update_news_status(news_item['_row_index'], new_status)
            return True
        return False

    def update_news_item(self, news_id, data):
        """Updates various fields of a news item by its news_id."""
        news_item = self.get_news_by_id(news_id)
        if not news_item:
            return False
            
        row_idx = news_item['_row_index']
        # Columns mapping: summary(2), media_url(10)
        if 'summary' in data:
            self.news_sheet.update_cell(row_idx, 2, data['summary'])
        if 'media_url' in data:
            self.news_sheet.update_cell(row_idx, 10, data['media_url'])
        if 'status' in data:
            self.news_sheet.update_cell(row_idx, 6, data['status'])
            
        return True

    # --- Content Queue Methods ---

    def add_content_row(self, topic, reel_url, ig_caption, fb_caption, li_caption, x_caption, platforms="all", schedule_time="now", status="Draft", user_id=""):
        """Adds generated content to the Content Queue after checking for duplicates."""
        if self.db is None:
            self.connect()
            
        # Deduplication check: Check if an identical draft already exists for this user
        records = self.content_sheet.get_all_records()
        for r in records:
            if (str(r.get('user_id', '')) == str(user_id) and 
                r.get('topic') == topic and 
                r.get('reel_url') == reel_url and 
                r.get('ig_caption') == ig_caption and 
                r.get('status') == 'Draft'):
                print(f"DBHelper: Duplicate draft detected for topic '{topic}'. Skipping insert.")
                # We return the existing row index (i + 2)
                for i, rec in enumerate(records):
                    if rec == r:
                        return i + 2
            
        row = [
            topic, reel_url, ig_caption, fb_caption, li_caption, x_caption, 
            platforms, str(schedule_time), status, 
            "", "", "", "", "", str(user_id)
        ]
        self.content_sheet.append_row(row)
        return len(self.content_sheet.get_all_values())

    def get_approved_content(self):
        """Returns all content rows with status 'Approved'."""
        if self.db is None:
            self.connect()
            
        records = self.content_sheet.get_all_records()
        approved = []
        for i, r in enumerate(records):
            if r.get('status') == 'Approved':
                r['_row_index'] = i + 2 
                approved.append(r)
        return approved

    def update_content_status(self, row_index, new_status, links=None, posted_at=None):
        """Updates the status and links of a published content row."""
        if self.db is None:
            self.connect()
            
        self.content_sheet.update_cell(row_index, 9, new_status) # Status is 9th col
        
        if links:
            # Update links if provided
            if 'ig' in links and links['ig']:
                self.content_sheet.update_cell(row_index, 10, links['ig'])
            if 'fb' in links and links['fb']:
                self.content_sheet.update_cell(row_index, 11, links['fb'])
            if 'li' in links and links['li']:
                self.content_sheet.update_cell(row_index, 12, links['li'])
            if 'x' in links and links['x']:
                self.content_sheet.update_cell(row_index, 13, links['x'])
                
        if posted_at:
            self.content_sheet.update_cell(row_index, 14, str(posted_at))
            
        return True
