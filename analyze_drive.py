import requests
import os
from dotenv import load_dotenv
from drive_helper import DriveHelper

load_dotenv()

def analyze_link():
    helper = DriveHelper()
    helper.connect()
    videos = helper.list_videos()
    if not videos:
        print("No videos found.")
        return
        
    video = videos[0]
    file_id = video['id']
    url = f"https://docs.google.com/uc?export=download&id={file_id}"
    
    print(f"Testing URL: {url}")
    # Simulating a bot/api download
    try:
        response = requests.get(url, stream=True, allow_redirects=True)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Headers: {dict(response.headers)}")
        
        # Check if we got HTML instead of video
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type:
            print("WARNING: Received HTML instead of a video stream. This likely contains a Google Virus Scan warning page, which blocks automated API downloads.")
        else:
            print(f"Success: Received {content_type}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_link()
