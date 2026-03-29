import time
import os
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
import db_content_helper as dbcontent

from db_sql_helper import get_api_key as sqlite_get_key

def upload_to_ayrshare_storage(local_path, user_id=None):
    """
    Uploads a local file to Ayrshare's media storage and returns the accessURL.
    This bypasses Google Drive's redirect issues.
    """
    api_key = None
    if user_id:
        api_key = sqlite_get_key(user_id, "ayrshare", "api_key")
    if not api_key:
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
    def post_content(cls, post_text, platforms, media_url=None, title=None, subreddit="test", user_id=None):
        api_key = None
        if user_id:
            api_key = sqlite_get_key(user_id, "ayrshare", "api_key")
        if not api_key:
            api_key = os.getenv("AYRSHARE_API_KEY")
        
        if not api_key:
            raise Exception("AYRSHARE_API_KEY is not set.")
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Platform Mapping
        ayrshare_platforms = []
        for p in platforms:
            p = p.lower().strip()
            if p in ["ig", "instagram"]: ayrshare_platforms.append("instagram")
            elif p in ["rd", "reddit"]: ayrshare_platforms.append("reddit")
            elif p in ["li", "linkedin"]: ayrshare_platforms.append("linkedin")
            elif p in ["fb", "facebook"]: ayrshare_platforms.append("facebook")
            elif p in ["x", "twitter"]: ayrshare_platforms.append("twitter")

        if not ayrshare_platforms:
            raise Exception("No valid platforms provided for Ayrshare.")

        # CLEAN TITLES & BODIES FOR PLATFORM CONTEXT
        # Reddit: No hashtags in title, no hashtags in body
        clean_title = re.sub(r'#\S+', '', title or "Social Media Update").strip()
        clean_body = re.sub(r'#\S+', '', post_text).strip()

        payload = {
            "post": post_text, # Default
            "platforms": ayrshare_platforms
        }

        # PLATFORM SPECIFIC OPTIONS (The "Seamless" Magic)
        if "reddit" in ayrshare_platforms:
            payload["redditOptions"] = {
                "subreddit": subreddit,
                "title": clean_title,
                "text": clean_body
            }
        
        if "linkedin" in ayrshare_platforms:
            payload["linkedinOptions"] = {
                "title": title or "New Post",
                "text": post_text
            }
            
        if "facebook" in ayrshare_platforms:
            payload["faceBookOptions"] = {
                "text": post_text
            }
            
        if "instagram" in ayrshare_platforms:
            # Instagram often fails if the caption is completely empty, 
            # so we ensure it has the original text with hashtags
            payload["instagramOptions"] = {
                "caption": post_text
            }

        if media_url:
            print(f"  -> [MEDIA WORKFLOW] Processing {media_url[:50]}...")
            
            is_cloudinary = "cloudinary.com" in media_url.lower()
            hints = [media_url, str(title), str(post_text)]
            is_image = any(any(ext in str(h).lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', 'image', 'picture', 'photo']) for h in hints)

            if is_cloudinary:
                print(f"  -> [MEDIA WORKFLOW] Cloudinary detected. Using direct URL.")
                payload["mediaUrls"] = [media_url]
                if "instagram" in ayrshare_platforms:
                    # Sync Reels toggle to IG specifically
                    payload["instagramOptions"]["reels"] = not is_image
            else:
                # Fallback to direct Drive link if provided
                if "/d/" in media_url or "id=" in media_url:
                    payload["mediaUrls"] = [get_direct_drive_url(media_url, is_image=is_image)]
                else:
                    payload["mediaUrls"] = [media_url]

        print(f"  -> [DEBUG] Final Ayrshare Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(cls.BASE_URL, json=payload, headers=headers, timeout=15.0)
        
        if response.status_code != 200:
            raise Exception(f"Ayrshare API Error {response.status_code}: {response.text}")
            
        result = response.json()
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


def run_publisher(user_id=None):
    print(f"[{datetime.now()}] Starting Publishing Agent for user {user_id or 'System'}...")
    
    approved_posts = dbcontent.get_approved_content()
    if not approved_posts:
        print("No 'Approved' posts waiting in the queue.")
        return

    for post in approved_posts:
        topic = post.get("topic", "Unknown")
        schedule_time = post.get("schedule_time", "now")
        row_index = post.get("row_index")
        
        if not is_time_to_post(schedule_time):
            continue
            
        print(f"\nPublishing: '{topic[:50]}...'")
        
        platforms_raw = str(post.get("platforms", "")).lower()
        platforms_to_post = []
        if platforms_raw == "all":
            platforms_to_post = ["instagram", "reddit", "linkedin", "facebook", "twitter"]
        else:
            platforms_to_post = [p.strip() for p in platforms_raw.split(",") if p.strip()]

        reel_url = post.get("reel_url", "")
        ig_caption = post.get("ig_caption", "")
        
        # Build the post context
        post_text = ig_caption
        
        links = {}
        has_errors = False
        try:
            link_id = AyrshareAPI.post_content(
                post_text=post_text, 
                platforms=platforms_to_post, 
                media_url=reel_url,
                title=topic,
                user_id=user_id
            )
            for p in platforms_to_post:
                links[p] = link_id
        except Exception as e:
            print(f"  -> [ERROR] Failed to post via Ayrshare: {e}")
            has_errors = True
                
        final_status = "Failed" if has_errors else "Posted"
        posted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            dbcontent.update_content_status(row_index, final_status, links, posted_time)
            print(f"[{topic[:30]}] Publication status: {final_status}")
        except Exception as e:
            print(f"Error updating DB status: {e}")

def publish_single(row_index, user_id=None):
    """Publish a specific row by its row_index."""
    print(f"[{datetime.now()}] Publishing single row {row_index} for user {user_id or 'System'}...")
    
    row_data = dbcontent.get_content_by_id(row_index)
    if not row_data:
        raise Exception(f"Row {row_index} not found")
    
    topic = row_data.get("topic", "Unknown")
    reel_url = row_data.get("reel_url", "")
    ig_caption = row_data.get("ig_caption", "")
    platforms_raw = str(row_data.get("platforms", "all")).lower()
    
    if platforms_raw == "all":
        platforms_to_post = ["instagram", "reddit", "linkedin", "facebook", "twitter"]
    else:
        platforms_to_post = [p.strip() for p in platforms_raw.split(",") if p.strip()]
    
    post_text = ig_caption
    
    try:
        link_id = AyrshareAPI.post_content(
            post_text=post_text,
            platforms=platforms_to_post,
            media_url=reel_url,
            title=topic,
            user_id=user_id
        )
        
        links = {p: link_id for p in platforms_to_post}
        posted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dbcontent.update_content_status(row_index, "Posted", links, posted_time)
        print(f"[{topic[:30]}] Published successfully!")
        return f"Published to {len(platforms_to_post)} platforms"
    except Exception as e:
        posted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dbcontent.update_content_status(row_index, "Failed", {}, posted_time)
        raise Exception(f"Publishing failed: {e}")


if __name__ == "__main__":
    run_publisher()
