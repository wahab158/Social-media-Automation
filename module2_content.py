import os
import json
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
from db_helper import DBHelper
from drive_helper import DriveHelper

# Load environment variables
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=groq_api_key) if groq_api_key else None

def generate_captions(topic, summary):
    """Uses OpenAI to generate platform-specific captions for IG, FB, LinkedIn, and X."""
    
    if not client:
        # Fallback if no OpenAI key
        print("Warning: OPENAI_API_KEY not set. Using fallback captions.")
        return {
            "ig": f"Here is the latest on {topic}! 🚀\n{summary}\n#tech #ai",
            "fb": f"What do you think about this? 🤔\n{topic}\n{summary}",
            "li": f"Important industry update regarding {topic}. {summary} #business",
            "x": f"{topic} is trending! {summary[:100]}... #tech"
        }

    prompt = f"""
    You are an expert Social Media Manager. Write 4 distinct social media captions for the following tech news:
    
    Topic/Headline: {topic}
    Summary: {summary}
    
    Rules for each platform:
    1. Instagram ("ig"): Max 2,200 chars. Strong hook in the first line. Use line breaks, generous emojis. 3-5 hashtags max. Call-to-action to save/tag. Assume video format.
    2. Facebook ("fb"): Storytelling format. 2-3 hashtags max. Ask a question to encourage comments. Include a link if relevant. 
    3. LinkedIn ("li"): Max 3,000 chars. Professional tone. Hook/statistic. 3-5 industry hashtags. Include a key takeaway. Minimal emojis (1-2 max).
    4. X/Twitter ("x"): STRICTLY LESS THAN 280 characters. Concise, punchy. 1-3 hashtags. Create curiosity. 
    
    Your response MUST be valid JSON in this exact format, with keys "ig", "fb", "li", "x". Do not include markdown code block formatting like ```json in your response, just the raw JSON object.
    {{
        "ig": "instagram caption text here...",
        "fb": "facebook caption text here...",
        "li": "linkedin caption text here...",
        "x": "x caption text here..."
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        
        output = response.choices[0].message.content.strip()
        # Clean up any potential markdown formatting
        if output.startswith("```json"):
            output = output[7:-3].strip()
        elif output.startswith("```"):
            output = output[3:-3].strip()
            
        captions = json.loads(output, strict=False)
        return captions
        
    except Exception as e:
        print(f"OpenAI caption generation error: {e}")
        return {
            "ig": "Error generating IG caption.",
            "fb": "Error generating FB caption.",
            "li": "Error generating LI caption.",
            "x": "Error generating X caption."
        }

def process_pending_news():
    print(f"[{datetime.now()}] Starting Content Creation Agent...")
    
    try:
        db = DBHelper()
        db.connect()
        drive = DriveHelper()
        drive.connect()
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # Check for available media in Drive
    try:
        drive_media = drive.list_media()
        print(f"Found {len(drive_media)} media files in Drive.")
    except Exception as e:
        print(f"Error listing Drive media: {e}")
        drive_media = []

    # Check for new news items
    pending_news = db.get_pending_news()
    
    if not pending_news:
        print("No new news items available in 'News Database'.")
        # Ask user if they want to enter manually
        choice = input("Would you like to enter a manual topic instead? (y/n): ")
        if choice.lower() == 'y':
            topic = input("Enter Headline/Topic: ")
            summary = input("Enter Summary: ")
            
            # Use Drive media if available
            reel_url = ""
            if drive_media:
                print("Available media from Drive:")
                for idx, v in enumerate(drive_media):
                    print(f"[{idx}] {v['name']}")
                v_choice = input(f"Select a media index (0-{len(drive_media)-1}) or enter a URL manually: ")
                if v_choice.isdigit() and 0 <= int(v_choice) < len(drive_media):
                    reel_url = drive_media[int(v_choice)]['webViewLink']
                    print(f"Selected: {drive_media[int(v_choice)]['name']}")
                else:
                    reel_url = v_choice
            else:
                reel_url = input("Enter Reel/Video URL (Required!): ")

            while not reel_url.strip():
                print("Error: Reel/Video URL is required by the system.")
                reel_url = input("Enter Reel/Video URL: ")
                
            captions = generate_captions(topic, summary)
            
            db.add_content_row(
                topic=topic,
                reel_url=reel_url,
                ig_caption=captions["ig"],
                fb_caption=captions["fb"],
                li_caption=captions["li"],
                x_caption=captions["x"],
                platforms="all", 
                schedule_time="now", 
                status="Draft"
            )
            print("Successfully manually generated and saved Content Queue Draft.")
        return

    print(f"Found {len(pending_news)} pending news items.")
    for news_item in pending_news:
        topic = news_item.get("title", "")
        summary = news_item.get("summary", "")
        row_index = news_item.get("_row_index")
        
        print(f"\nProcessing '{topic[:50]}...'")
        
        # User input required or select from Drive
        reel_url = ""
        if drive_media:
             preferred_media = drive_media[0]
             # Prefer webContentLink for direct Ayrshare API downloads, fallback to webViewLink
             reel_url = preferred_media.get('webContentLink', preferred_media.get('webViewLink'))
             print(f"Auto-selected media from Drive: {preferred_media['name']} ({preferred_media.get('mimeType')})")
             # Rotate media to the end of the list to reuse it across many news items
             drive_media.append(drive_media.pop(0))
        else:
            print(f"No Drive videos found. Using a fallback media URL for '{topic[:30]}...'")
            reel_url = "https://img.ayrshare.com/012/gb.jpg"
            
        # 1. Generate 4 captions
        print("Generating AI captions...")
        captions = generate_captions(topic, summary)
        
        # 2. Save to Content Queue
        try:
            db.add_content_row(
                topic=topic,
                reel_url=reel_url,
                ig_caption=captions.get("ig", ""),
                fb_caption=captions.get("fb", ""),
                li_caption=captions.get("li", ""),
                x_caption=captions.get("x", ""),
                platforms="all",    # Defaults
                schedule_time="now", 
                status="Draft"
            )
            print("Successfully added to Content Queue as 'Draft'.")
            
            # 3. Mark news item as Used
            db.update_news_status(row_index, "Used")
            
        except Exception as e:
            print(f"Error saving to Content Queue: {e}")

if __name__ == "__main__":
    process_pending_news()
