import time
import os
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from db_helper import DBHelper

load_dotenv()

def upload_to_ayrshare_storage(local_path):
    """
    Uploads a local file to Ayrshare's media storage and returns the accessURL.
    This bypasses Google Drive's redirect issues.
    """
    api_key = os.getenv("AYRSHARE_API_KEY")
    url = "https://api.ayrshare.com/api/media/upload"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    print(f"  -> [AYRSHARE STORAGE] Uploading {os.path.basename(local_path)}...")
    with open(local_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, headers=headers, files=files)
        
    if response.status_code != 200:
        raise Exception(f"Ayrshare Storage Upload Error {response.status_code}: {response.text}")
        
    data = response.json()
    access_url = data.get("accessUrl")
    print(f"  -> [AYRSHARE STORAGE] Success: {access_url}")
    return access_url

def get_direct_drive_url(original_url, is_image=False):
    """
    Ensures the Drive URL is transformed into a format Instagram's 
    ingest server can resolve.
    'is_image' defaults to False but can be set if we know the mime type.
    """
    # Extract the file ID using regex
    file_id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', original_url)
    if not file_id_match:
        # Fallback for uc?id= style links
        file_id_match = re.search(r'id=([a-zA-Z0-9_-]+)', original_url)
    
    if file_id_match:
        file_id = file_id_match.group(1)
        if is_image:
            # LH3 is a direct, static, no-redirect format for images
            return f"https://lh3.googleusercontent.com/d/{file_id}"
        else:
            # Standard uc for videos
            return f"https://drive.google.com/uc?export=download&id={file_id}&ext=.mp4"
    
    return original_url

def verify_link_accessibility(url):
    """Checks if the link is reachable and returns the mime type."""
    try:
        # Use GET with stream=True and allow_redirects to see the REAL final mime type
        # We only need the headers, so we close it immediately
        with requests.get(url, stream=True, allow_redirects=True, timeout=10) as response:
            if response.status_code == 200:
                mime_type = response.headers.get('Content-Type', '')
                print(f"  -> [URL VERIFICATION] Success: {url[:60]}... (Type: {mime_type})")
                return True, mime_type
            else:
                print(f"  -> [URL VERIFICATION] Warning: Link returned status {response.status_code}")
                return False, None
    except Exception as e:
        print(f"  -> [URL VERIFICATION] Connection error: {e}")
        return False, None

class AyrshareAPI:
    """API integration for Ayrshare to post to multiple social platforms simultaneously."""
    
    BASE_URL = "https://api.ayrshare.com/api/post"
    
    @classmethod
    def post_content(cls, post_text, platforms, media_url=None, title=None, subreddit="test"):
        api_key = os.getenv("AYRSHARE_API_KEY")
        if not api_key:
            raise Exception("AYRSHARE_API_KEY is not set.")
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Ayrshare platform keys
        ayrshare_platforms = []
        for p in platforms:
            p = p.lower().strip()
            if p in ["ig", "instagram"]: ayrshare_platforms.append("instagram")
            elif p in ["rd", "reddit"]: ayrshare_platforms.append("reddit")
            elif p in ["li", "linkedin"]: ayrshare_platforms.append("linkedin")

        if not ayrshare_platforms:
            raise Exception("No valid platforms (IG/Reddit) provided for Ayrshare.")

        payload = {
            "post": post_text,
            "platforms": ayrshare_platforms
        }
        
        # Reddit specifics
        if "reddit" in ayrshare_platforms:
            payload["subreddit"] = subreddit
            payload["title"] = title if title else "Social Media Update"

        if media_url:
            print(f"  -> [MEDIA WORKFLOW] Processing {media_url[:50]}...")
            
            # Step 1: Detect file ID
            file_id = None
            if "/d/" in media_url:
                file_id = media_url.split("/d/")[1].split("/")[0]
            elif "id=" in media_url:
                file_id = media_url.split("id=")[1].split("&")[0]

            # Better is_image detection using multiple sources
            hints = [media_url, str(title), str(post_text)]
            is_image = any(any(ext in str(h).lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', 'image', 'picture', 'photo']) for h in hints)

            if file_id:
                try:
                    # Step 2: Verification of type
                    temp_direct = f"https://drive.google.com/uc?export=download&id={file_id}"
                    accessible, mime_type = verify_link_accessibility(temp_direct)
                    
                    if accessible and mime_type:
                        is_image = 'image/' in mime_type
                    
                    print(f"  -> [MEDIA WORKFLOW] Type: {mime_type if accessible else 'Unknown'} (is_image: {is_image})")

                    # Step 3: Download locally using requests (simpler/more reliable for public files)
                    ext = ".jpg" if is_image else ".mp4"
                    local_path = os.path.join(os.getcwd(), f"temp_{file_id}{ext}")
                    
                    print(f"  -> [MEDIA WORKFLOW] Downloading to {local_path}...")
                    with requests.get(temp_direct, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        with open(local_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    
                    # Step 4: Upload to Ayrshare Storage
                    clean_url = upload_to_ayrshare_storage(local_path)
                    
                    # Clean up local file
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    
                    payload["mediaUrls"] = [clean_url]
                    
                    # Step 5: Platform specific toggles
                    if "instagram" in ayrshare_platforms:
                        payload["reels"] = not is_image
                            
                except Exception as e:
                    print(f"  -> [MEDIA WORKFLOW ERROR] {e}")
                    print(f"  -> [AYRSHARE warning] Fallback to direct Drive link (is_image: {is_image})")
                    payload["mediaUrls"] = [get_direct_drive_url(media_url, is_image=is_image)]
            else:
                # Not a Drive link? Just use it as is
                payload["mediaUrls"] = [media_url]

        print(f"  -> [DEBUG] Final Ayrshare Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(cls.BASE_URL, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Ayrshare API Error {response.status_code}: {response.text}")
            
        result = response.json()
        print(f"  -> [AYRSHARE POST SUCCESS] Platforms: {ayrshare_platforms}")
        
        post_ids = result.get("postIds", [])
        return f"Ayrshare ID: {result.get('id', 'Unknown')} (Posted to {len(post_ids)} platforms)"


def is_time_to_post(schedule_time_str):
    """Checks if the scheduled time has passed."""
    if not schedule_time_str or str(schedule_time_str).strip().lower() == "now":
        return True
    try:
        schedule = datetime.strptime(str(schedule_time_str).strip(), "%Y-%m-%d %H:%M")
        return datetime.now() >= schedule
    except ValueError:
        return True


def run_publisher():
    print(f"[{datetime.now()}] Starting Publishing Agent...")
    
    try:
        db = DBHelper()
        db.connect()
    except Exception as e:
        print(f"Database connection error: {e}")
        return

    approved_posts = db.get_approved_content()
    if not approved_posts:
        print("No 'Approved' posts waiting in the queue.")
        return

    for post in approved_posts:
        topic = post.get("topic", "Unknown")
        schedule_time = post.get("schedule_time", "now")
        row_index = post.get("_row_index")
        
        if not is_time_to_post(schedule_time):
            continue
            
        print(f"\nPublishing: '{topic[:50]}...'")
        
        platforms_raw = str(post.get("platforms", "")).lower()
        platforms_to_post = []
        if platforms_raw == "all":
            platforms_to_post = ["instagram", "reddit"]
        else:
            platforms_to_post = [p.strip() for p in platforms_raw.split(",") if p.strip()]

        reel_url = post.get("reel_url", "")
        ig_caption = post.get("ig_caption", "")
        
        # Reddit cleanup: No hashtags in title, no divider/link in body
        # Strip hashtags from topic for the title
        reddit_title = re.sub(r'#\S+', '', topic).strip()
        reddit_body = ig_caption # Use the clean caption without the Drive link

        # Use the IG caption as base for the 'post' field
        post_text = reddit_body if "reddit" in platforms_to_post or "rd" in platforms_to_post else ig_caption
        
        links = {}
        has_errors = False
        try:
            link_id = AyrshareAPI.post_content(
                post_text=post_text, 
                platforms=platforms_to_post, 
                media_url=reel_url,
                title=reddit_title
            )
            for p in platforms_to_post:
                links[p] = link_id
        except Exception as e:
            print(f"  -> [ERROR] Failed to post via Ayrshare: {e}")
            has_errors = True
                
        final_status = "Failed" if has_errors else "Posted"
        posted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            db.update_content_status(row_index, final_status, links, posted_time)
            print(f"[{topic[:30]}] Publication status: {final_status}")
        except Exception as e:
            print(f"Error updating Sheet status: {e}")

if __name__ == "__main__":
    run_publisher()
