import time
from datetime import datetime
from db_helper import DBHelper

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

class AyrshareAPI:
    """API integration for Ayrshare to post to multiple social platforms simultaneously."""
    
    BASE_URL = "https://api.ayrshare.com/api/post"
    
    @classmethod
    def post_content(cls, post_text, platforms, media_url=None):
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
            p = p.lower()
            if p in ["ig", "instagram"]: ayrshare_platforms.append("instagram")
            elif p in ["rd", "reddit"]: ayrshare_platforms.append("reddit")
            # Ignoring FB, X, LI for now as requested by user to focus on IG and Reddit

        if not ayrshare_platforms:
            raise Exception("No valid platforms provided for Ayrshare.")

        payload = {
            "post": post_text,
            "platforms": ayrshare_platforms
        }
        
        # Reddit specific requirements
        if "reddit" in ayrshare_platforms:
            # Ayrshare needs a subreddit name. We'll default to 'test' or 'technology'
            # Or we can extract it if the user provides it.
            payload["subreddit"] = "test" 
            # The first line of 'post' is usually used as title, but we can be explicit
            title = post_text.split('\n')[0]
            payload["title"] = title[:300] # Reddit title limit
        
        if media_url:
            # We must use direct download links for Google Drive, not web viewers.
            direct_link = media_url
            if "drive.google.com/file/d/" in media_url or "drive.google.com/uc?" in media_url:
                file_id = ""
                if "/d/" in media_url:
                    file_id = media_url.split("/d/")[1].split("/")[0]
                elif "id=" in media_url:
                    file_id = media_url.split("id=")[1].split("&")[0]
                
                if file_id:
                    # Using docs.google.com/uc?export=download&id= is often more reliable for external APIs
                    direct_link = f"https://docs.google.com/uc?export=download&id={file_id}"
            
            payload["mediaUrls"] = [direct_link]

        print(f"  -> [DEBUG] Final Ayrshare Payload: {json.dumps(payload, indent=2)}")

        response = requests.post(cls.BASE_URL, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Ayrshare API Error {response.status_code}: {response.text}")
            
        result = response.json()
        print(f"  -> [AYRSHARE POST SUCCESS] Platforms: {ayrshare_platforms}")
        
        # Return a tracking link or ID
        post_ids = result.get("postIds", [])
        return f"Ayrshare ID: {result.get('id', 'Unknown')} (Posted to {len(post_ids)} platforms)"


def is_time_to_post(schedule_time_str):
    """Checks if the scheduled time has passed."""
    if not schedule_time_str or str(schedule_time_str).strip().lower() == "now":
        return True
        
    try:
        # Example format expectation: "2026-03-05 14:00"
        schedule = datetime.strptime(str(schedule_time_str).strip(), "%Y-%m-%d %H:%M")
        if datetime.now() >= schedule:
            return True
        return False
    except ValueError:
        # If the format is wrong, default to posting now to prevent it getting stuck
        print(f"Warning: Could not parse schedule time '{schedule_time_str}'. Defaulting to 'now'.")
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

    print(f"Found {len(approved_posts)} 'Approved' post(s). Checking schedules...")
    
    for post in approved_posts:
        topic = post.get("topic", "Unknown")
        schedule_time = post.get("schedule_time", "now")
        row_index = post.get("_row_index")
        
        if not is_time_to_post(schedule_time):
            print(f"[{topic[:30]}] is scheduled for {schedule_time}. Skipping for now.")
            continue
            
        print(f"\nPublishing: '{topic[:50]}...'")
        
        platforms_raw = str(post.get("platforms", "")).lower()
        platforms_to_post = []
        if platforms_raw == "all":
            platforms_to_post = ["fb", "ig", "li", "x"]
        else:
            # Parse something like "fb,ig"
            platforms_to_post = [p.strip() for p in platforms_raw.split(",") if p.strip()]

        reel_url = post.get("reel_url", "")
        links = {}
        has_errors = False
        
        # Construct the optimal post text. Note: Ayrshare takes a primary post.
        # We can use the IG caption as the base since Instagram and Reddit are the targets
        post_text = post.get("ig_caption", "")
        if "Error generating" in post_text or not post_text:
             post_text = f"Check out this viral trend: {topic}\n\n#tech #trending"
             
        # Reddit requires a title (which Ayrshare extracts from the first line)
        if "reddit" in platforms_to_post or "rd" in platforms_to_post:
             post_text = f"{topic}\n\n{post_text}"
             # Workaround: Append the video link to the body for Reddit since direct video upload isn't supported via Ayrshare API
             if reel_url:
                 post_text += f"\n\nWatch Video: {reel_url}"
             
        # Ayrshare Call
        try:
            link_id = AyrshareAPI.post_content(post_text, platforms_to_post, reel_url)
            # We'll just assign this common link ID to all requested platforms to record in DB
            for p in platforms_to_post:
                links[p] = link_id
        except Exception as e:
            print(f"  -> [ERROR] Failed to post via Ayrshare: {e}")
            has_errors = True
                
        # Final Status Decision
        final_status = "Failed" if has_errors else "Posted"
        posted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            db.update_content_status(row_index, final_status, links, posted_time)
            if has_errors:
                print(f"Post marked as 'Failed' due to platform errors. (Retries can be managed manually by reviewing).")
            else:
                print(f"Successfully published to targeted platforms! Status updated to 'Posted'.")
        except Exception as e:
            print(f"Error updating Sheet status: {e}")

if __name__ == "__main__":
    run_publisher()
