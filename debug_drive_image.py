import requests
import os
from dotenv import load_dotenv

load_dotenv()

def debug_image_link():
    file_id = "1y4WBt4LOUtjT-aBIS4TeAskIyPiRtUOC"
    url = f"https://drive.google.com/uc?export=download&id={file_id}&ext=.jpg"
    
    print(f"Testing URL: {url}")
    try:
        response = requests.get(url, allow_redirects=True, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if 'text/html' in response.headers.get('Content-Type', ''):
            print("\nPage Content Snippet:")
            print(response.text[:1000]) # First 1000 chars
        else:
            print("Received direct file!")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_image_link()
