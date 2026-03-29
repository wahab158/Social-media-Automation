import os
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import db_content_helper as dbcontent
from drive_helper import DriveHelper
from cloudinary_helper import CloudinaryHelper

from db_sql_helper import get_api_key as sqlite_get_key, get_brand_profiles
import requests

# Load environment variables
load_dotenv()

def get_groq_client(user_id):
    """Initializes Groq client using user's API key, or falls back to env var."""
    api_key = None
    if user_id:
        api_key = sqlite_get_key(user_id, "groq", "api_key")
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY")
    return  Groq(api_key=api_key) if api_key else None

ARCHETYPE_PROMPTS = {
    "sage":     "You are a trusted expert. Teach clearly, cite data, build authority.",
    "maverick": "You are bold and contrarian. Challenge assumptions, spark debate.",
    "creator":  "You are imaginative and inspiring. Paint visions, use vivid language.",
    "mentor":   "You are warm and encouraging. Speak directly to the reader's growth.",
    "curator":  "You are selective and discerning. Only share what genuinely matters."
}

EMOJI_DENSITY = {
    1: "Use zero emojis. Pure text only.",
    2: "Use 1 to 2 emojis maximum per post.",
    3: "Use 3 to 5 emojis placed at natural pauses.",
    4: "Use emojis freely to add energy and visual rhythm.",
    5: "Use emojis extensively as a core part of the visual style."
}

def load_brand_identity(user_id=None):
    """Reads the active brand profile for persona, rules, and platform toggles."""
    default_prompt = "You are a professional social media manager. Tone: Informative, Engaging, and Professional."
    default_toggles = {"instagram": True, "linkedin": True, "facebook": True, "x": True, "tiktok": True}
    
    if not user_id:
        return default_prompt, default_toggles
        
    try:
        profiles = get_brand_profiles(user_id)
        active = next((p for p in profiles if p.get("is_active")), profiles[0] if profiles else None)
        if not active:
            return default_prompt, default_toggles
            
        dna = {}
        try: dna = json.loads(active.get("dna_config_json") or "{}")
        except: pass
        
        toggles = {}
        try: toggles = json.loads(active.get("platform_toggles") or "{}")
        except: pass
        if not toggles: toggles = default_toggles
        
        sys_inst = active.get("system_instruction") or ""
        archetype = dna.get("archetype", "sage")
        emoji_str = int(dna.get("emoji_strategy", 2))
        
        prompt = f"SYSTEM INSTRUCTION:\n{sys_inst}\n\nYOUR ARCHETYPE:\n{ARCHETYPE_PROMPTS.get(archetype, ARCHETYPE_PROMPTS['sage'])}\n\nEMOJI RULE:\n{EMOJI_DENSITY.get(emoji_str, EMOJI_DENSITY[2])}"
        return prompt, toggles
    except Exception as e:
        print(f"Error loading brand identity: {e}")
        return default_prompt, default_toggles

def generate_captions(topic, summary, client, user_id=None):
    """Uses Groq to generate platform-specific captions with Brand DNA injection."""
    
    brand_rules, platform_toggles = load_brand_identity(user_id)
    
    if not client:
        # Fallback if no API key
        print("Warning: GROQ_API_KEY not set. Using fallback captions.")
        return {
            "ig": f"Here is the latest on {topic}! 🚀\n{summary}\n#tech #ai",
            "fb": f"What do you think about this? 🤔\n{topic}\n{summary}",
            "li": f"Important industry update regarding {topic}. {summary} #business",
            "x": f"{topic} is trending! {summary[:100]}... #tech"
        }
    
    prompt = f"""
    {brand_rules}
    
    TASK:
    You are the Social Media Content Creator for the brand above. 
    Write 4 distinct, high-impact social media captions based on the following content:
    
    CONTENT CONTEXT:
    Topic: {topic}
    Description/Details: {summary}
    
    STRICT CONTENT RULES (OVERRIDE BRAND IF CONFLICT):
    1. NEVER mention technical terms like "Cloudinary", "pinned image", "media link", "URL", "Vision AI", or "extracted text".
    2. Treat visual details as your own direct observation.
    3. Instagram, Facebook, LinkedIn: MINIMUM 15-20 lines of text. Use a storytelling approach.
    4. Layout: Use headers like [THE NEWS], [CONTEXT], [IMPLICATIONS] where appropriate.
    5. Hashtags: Exactly 7 hashtags at the very bottom.
    
    PLATFORM SPECIFICS:
    - IG: Max 2200 chars. Story hook at the start.
    - FB: Engaging and community-focused.
    - LI: Insightful, professional, career-relevant. Use bullets for key points.
    - X: Max 280 chars. Sharp headline format.
    
    OUTPUT FORMAT:
    Return ONLY a raw JSON object. Use double quotes.
    {{
      "ig": "long caption here...",
      "fb": "long caption here...",
      "li": "long caption here...",
      "x": "short tweet here..."
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7,
            timeout=30.0
        )
        
        output = response.choices[0].message.content.strip()
        
        # Robust parsing logic
        try:
            # Clean possible markdown artifacts
            clean_output = output
            if "```json" in clean_output:
                clean_output = clean_output.split("```json")[-1].split("```")[0].strip()
            elif "```" in clean_output:
                clean_output = clean_output.split("```")[-1].split("```")[0].strip()
            
            # Find the first { and last }
            start = clean_output.find('{')
            end = clean_output.rfind('}')
            if start != -1 and end != -1:
                json_str = clean_output[start:end+1]
                res_dict = json.loads(json_str, strict=False)
                
                # Filter out platforms disabled in brand profile
                filtered_res = {}
                if platform_toggles.get("instagram", True): filtered_res["ig"] = res_dict.get("ig", "")
                if platform_toggles.get("facebook", True): filtered_res["fb"] = res_dict.get("fb", "")
                if platform_toggles.get("linkedin", True): filtered_res["li"] = res_dict.get("li", "")
                if platform_toggles.get("x", True): filtered_res["x"] = res_dict.get("x", "")
                
                return filtered_res
            else:
                raise ValueError("No valid JSON found in response")
        except Exception as e:
            print(f"Caption JSON parse error: {e}\nRaw output: {output}")
            raise e
        
    except Exception as e:
        print(f"Groq caption generation error: {e}")
        return {
            "ig": "Error generating IG caption. Please try refining manually.",
            "fb": "Error generating FB caption.",
            "li": "Error generating LI caption.",
            "x": "Error generating X caption."
        }

def generate_from_single_news(user_id, news_id):
    """
    Generates a draft from a specific news item fetched from the db by news_id.
    It uploads the article's image to Cloudinary to ensure platform previews work.
    """
    print(f"[{datetime.now()}] Generating post from news {news_id} for user {user_id or 'System'}")
    
    try:
        news_item = dbcontent.get_news_by_id(news_id)
        if not news_item:
            return {"success": False, "error": "News item not found."}
            
        topic = news_item.get("title", "")
        summary = news_item.get("summary", "")
        source_url = news_item.get("source_url", "")
        
        # 1. Handle Media (Prioritize news item media_url)
        final_media_url = news_item.get("media_url", "")
        if not final_media_url:
            final_media_url = ""
            
        # 2. Generate Captions
        client = get_groq_client(user_id)
        
        # Append attribution to prompt context
        extended_summary = f"{summary}\nSource: {source_url}"
        captions = generate_captions(topic, extended_summary, client, user_id)
        
        new_idx = dbcontent.add_content_row(
            topic=topic,
            reel_url=final_media_url,
            ig_caption=captions.get("ig", ""),
            fb_caption=captions.get("fb", ""),
            li_caption=captions.get("li", ""),
            x_caption=captions.get("x", ""),
            platforms="all",
            schedule_time="now",
            status="Draft",
            user_id=user_id
        )
        
        # 4. Mark News as Used
        dbcontent.update_news_status_by_id(news_id, "Used")
        
        return {
            "success": True, 
            "row_index": new_idx, 
            "topic": topic,
            "caption": captions.get("ig", ""),
            "reel_url": final_media_url
        }

        
    except Exception as e:
        print(f"Error generating from news: {e}")
        return {"success": False, "error": str(e)}

def generate_custom_post(user_id, custom_text):
    """
    Directly generates a draft from user-provided custom news text.
    """
    print(f"[{datetime.now()}] Generating custom post for user {user_id or 'System'}")
    
    try:
        # Use AI to extract a short topic/title from the raw text
        client = get_groq_client(user_id)
        if client:
            try:
                topic_res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": f"Extract a short 3-6 word news headline for this text:\n\n{custom_text}"}],
                    max_tokens=20
                )
                topic = topic_res.choices[0].message.content.strip().strip('"')
            except:
                topic = custom_text[:50] + "..."
        else:
            topic = custom_text[:50] + "..."
            
        final_media_url = ""
        # 2. Generate Captions
        captions = generate_captions(topic, custom_text, client, user_id)
            
        new_idx = dbcontent.add_content_row(
            topic=topic,
            reel_url=final_media_url,
            ig_caption=captions.get("ig", ""),
            fb_caption=captions.get("fb", ""),
            li_caption=captions.get("li", ""),
            x_caption=captions.get("x", ""),
            platforms="all",
            schedule_time="now",
            status="Draft",
            user_id=user_id
        )
        
        return {
            "success": True, 
            "row_index": new_idx, 
            "topic": topic,
            "caption": captions.get("ig", ""),
            "reel_url": final_media_url
        }

    except Exception as e:
        print(f"Error generating custom post: {e}")
        return {"success": False, "error": str(e)}

def process_pending_news_auto(media_url=None, user_id=None):
    """Non-interactive version for API/server use. No input() calls."""
    print(f"[{datetime.now()}] Starting Content Creation Agent (Auto Mode)...")
    
    # Check for new news items
    pending_news = dbcontent.get_pending_news()
    
    if not pending_news:
        print("No pending news items to process.")
        return 0, [], None

    count = 0
    new_row_indices = []
    print(f"Found {len(pending_news)} pending news items.")
    for news_item in pending_news:
        topic = news_item.get("title", "")
        summary = news_item.get("summary", "")
        row_index = news_item.get("_row_index")
        
        print(f"\nProcessing '{topic[:50]}...'")
        
        reel_url = news_item.get("media_url") or fallback_media_url
            
        # Generate captions
        print("Generating AI captions...")
        client = get_groq_client(user_id)
        captions = generate_captions(topic, summary, client, user_id)
        
        try:
            # db.add_content_row now returns the row index it was added to
            new_idx = dbcontent.add_content_row(
                topic=topic,
                reel_url=reel_url,
                ig_caption=captions.get("ig", ""),
                fb_caption=captions.get("fb", ""),
                li_caption=captions.get("li", ""),
                x_caption=captions.get("x", ""),
                platforms="all",
                schedule_time="now", 
                status="Draft",
                user_id=user_id
            )
            print(f"Added to Content Queue as 'Draft' at row {new_idx}")
            news_id_val = news_item.get('news_id')
            if news_id_val:
                dbcontent.update_news_status_by_id(news_id_val, "Used")
            count += 1
            new_row_indices.append(new_idx)
        except Exception as e:
            print(f"Error saving to Content Queue: {e}")
    
    first_draft = None
    if new_row_indices:
        # We only need the first one for the UI preview
        first_draft = {
            "topic": pending_news[0].get("title", ""),
            "caption": captions.get("ig", ""),
            "row_index": new_row_indices[0],
            "reel_url": reel_url
        }
    
    return count, new_row_indices, first_draft


def process_pending_news():
    """CLI-interactive version (for manual terminal use only)."""
    process_pending_news_auto()

if __name__ == "__main__":
    process_pending_news()
