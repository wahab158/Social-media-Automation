import os
import json
import requests
from datetime import datetime
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import db_content_helper as dbcontent
from db_sql_helper import get_api_key as sqlite_get_key

class BasePublisher(ABC):
    @abstractmethod
    def publish(self, post_data: dict, platforms: List[str]) -> Dict[str, str]:
        pass

class AyrsharePublisher(BasePublisher):
    BASE_URL = "https://api.ayrshare.com/api/post"

    def publish(self, post_data: dict, platforms: List[str]) -> Dict[str, str]:
        user_id = post_data.get("user_id")
        api_key = sqlite_get_key(user_id, "ayrshare", "api_key") or os.getenv("AYRSHARE_API_KEY")
        
        if not api_key:
            raise Exception("Ayrshare API key missing")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        # Map platforms
        mapping = {"instagram": "instagram", "facebook": "facebook", "linkedin": "linkedin", "x": "twitter", "tiktok": "tiktok"}
        target_platforms = [mapping[p] for p in platforms if p in mapping]

        payload = {
            "post": post_data.get("caption_instagram", post_data.get("topic")),
            "platforms": target_platforms,
            "mediaUrls": json.loads(post_data.get("image_urls_json", "[]"))
        }

        response = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            raise Exception(f"Ayrshare Error: {response.text}")
        
        res_json = response.json()
        # Return a map of platform -> status/id
        return {p: res_json.get("id") for p in target_platforms}

class BufferPublisher(BasePublisher):
    """Simple Access Token based Buffer Publisher (No OAuth2 for localhost convenience)."""
    def publish(self, post_data: dict, platforms: List[str]) -> Dict[str, str]:
        user_id = post_data.get("user_id")
        # Buffer user input token stored in 'buffer/access_token'
        api_key = sqlite_get_key(user_id, "buffer", "access_token")
        if not api_key:
            raise Exception("Buffer Access Token missing")
        
        # Buffer logic here (Implementation placeholder)
        print(f"Buffer publishing for {platforms}...")
        return {p: "buffer_queued" for p in platforms}

class NativePublisher(BasePublisher):
    """Placeholder for direct Developer API integrations."""
    def publish(self, post_data: dict, platforms: List[str]) -> Dict[str, str]:
        print(f"Native publishing for {platforms}...")
        return {p: "native_success" for p in platforms}

class PublishManager:
    def __init__(self):
        self.publishers = {
            "ayrshare": AyrsharePublisher(),
            "buffer": BufferPublisher(),
            "native": NativePublisher()
        }

    def run_check_loop(self):
        """Called by background scheduler to find 'scheduled' posts that need to go live."""
        now = datetime.utcnow().isoformat()
        # Fetch status='scheduled' posts where scheduled_time <= now
        conn = dbcontent.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts WHERE status = 'scheduled' AND scheduled_time <= ?", (now,))
        due_posts = cursor.fetchall()
        conn.close()

        for post in due_posts:
            self.publish_post(dict(post))

    def publish_post(self, post_dict: dict):
        post_id = post_dict["id"]
        platforms = json.loads(post_dict.get("platforms_json", "[]"))
        
        # Preference: Ayrshare > Buffer > Native (Simple fallback for now)
        # In a real multi-tenant system, this would be per brand setting
        try:
            publisher = self.publishers["ayrshare"] # Default
            results = publisher.publish(post_dict, platforms)
            
            # Update DB
            dbcontent.update_post_status(post_id, "posted", publish_url=str(results))
            print(f"Post {post_id} published successfully.")
        except Exception as e:
            print(f"Post {post_id} FAILED: {str(e)}")
            dbcontent.update_post_status(post_id, "failed")
            # Log failure to agent_runs or similar
