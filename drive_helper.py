import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# Define the scopes required for Google Drive API
SCOPES = ['https://www.googleapis.com/auth/drive']

class DriveHelper:
    def __init__(self, folder_id=None, credentials_path=None):
        self.folder_id = folder_id or os.getenv('GOOGLE_DRIVE_FOLDER_ID', '1G3IJ34Sp9KYub0rk9xsxl5Yhk5-T2X3l')
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
        self.service = None

    def connect(self):
        """Connects to Google Drive using service account credentials."""
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
        
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=SCOPES)
        self.service = build('drive', 'v3', credentials=creds)

    def list_videos(self):
        """Lists video files in the specified folder that haven't been processed."""
        if self.service is None:
            self.connect()

        # Query for video files in the specific folder
        # We can look for mimeType starting with 'video/'
        query = f"'{self.folder_id}' in parents and mimeType contains 'video/' and trashed = false"
        results = self.service.files().list(
            q=query,
            pageSize=10,
            fields="nextPageToken, files(id, name, mimeType, webViewLink, webContentLink)"
        ).execute()
        
        return results.get('files', [])

    def get_video_link(self, file_id):
        """Returns the webViewLink for a specific file."""
        if self.service is None:
            self.connect()
            
        file = self.service.files().get(fileId=file_id, fields='webViewLink').execute()
        return file.get('webViewLink')

if __name__ == "__main__":
    # Quick test
    try:
        helper = DriveHelper()
        print("Connecting to Drive...")
        helper.connect()
        print("Listing videos...")
        videos = helper.list_videos()
        if not videos:
            print("No videos found in the specified folder.")
        for v in videos:
            print(f"Found Video: {v['name']} (ID: {v['id']})")
            print(f"Link: {v['webViewLink']}")
    except Exception as e:
        print(f"Error: {e}")
