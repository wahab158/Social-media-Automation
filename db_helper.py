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
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
        
        if not self.sheet_url or self.sheet_url == "https://docs.google.com/spreadsheets/d/your-sheet-id/edit":
            raise ValueError("GOOGLE_SHEET_URL is not set or is still the default example.")

        creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.db = self.client.open_by_url(self.sheet_url)
        
        # Ensure sheets exist
        try:
            self.news_sheet = self.db.worksheet("News Database")
        except gspread.WorksheetNotFound:
            self.news_sheet = self.db.add_worksheet(title="News Database", rows="1000", cols="20")
            # Setup headers
            self.news_sheet.append_row(["title", "summary", "category", "source_url", "date_found", "status"])

        try:
            self.content_sheet = self.db.worksheet("Content Queue")
        except gspread.WorksheetNotFound:
            self.content_sheet = self.db.add_worksheet(title="Content Queue", rows="1000", cols="20")
            # Setup headers
            headers = ["topic", "reel_url", "ig_caption", "fb_caption", "li_caption", "x_caption", "platforms", 
                       "schedule_time", "status", "ig_post_url", "fb_post_url", "li_post_url", "x_post_url", "posted_at"]
            self.content_sheet.append_row(headers)

    # --- News Database Methods ---

    def add_news_row(self, title, summary, category, source_url, date_found, status="New"):
        """Adds a new row to the News Database. Avoids duplicates by checking source_url."""
        if self.db is None:
            self.connect()
            
        # Check for duplicates using the source_url (4th column)
        urls = self.news_sheet.col_values(4) 
        if source_url in urls:
            return False # Duplicate found
            
        row = [title, summary, category, source_url, str(date_found), status]
        self.news_sheet.append_row(row)
        return True

    def get_pending_news(self):
        """Returns all news rows with status 'New'."""
        if self.db is None:
            self.connect()
        
        records = self.news_sheet.get_all_records()
        pending = []
        for i, r in enumerate(records):
            if r.get('status') == 'New':
                # Save the row index (gspread is 1-indexed, and we skip header, so +2)
                r['_row_index'] = i + 2 
                pending.append(r)
        return pending
        
    def update_news_status(self, row_index, new_status):
        """Updates the status of a news item after it has been used."""
        if self.db is None:
            self.connect()
            
        # status is the 6th column
        self.news_sheet.update_cell(row_index, 6, new_status) 
        return True

    # --- Content Queue Methods ---

    def add_content_row(self, topic, reel_url, ig_caption, fb_caption, li_caption, x_caption, platforms="all", schedule_time="now", status="Draft"):
        """Adds generated content to the Content Queue."""
        if self.db is None:
            self.connect()
            
        row = [
            topic, reel_url, ig_caption, fb_caption, li_caption, x_caption, 
            platforms, str(schedule_time), status, 
            "", "", "", "", "" # Empty placeholders for the 4 post URLs and posted_at
        ]
        self.content_sheet.append_row(row)
        return True

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
