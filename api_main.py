from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from groq import Groq

from db_helper import DBHelper
from drive_helper import DriveHelper

# Module Imports for tool-calling
from module1_news import run_news_agent
from module2_content import process_pending_news
from module4_publisher import run_publisher

app = FastAPI(title="Social Media Automation Dashboard API")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DBHelper()
drive = DriveHelper()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ContentRow(BaseModel):
    row_index: int
    topic: str
    reel_url: str
    status: str
    platforms: str
    schedule_time: str
    ig_caption: Optional[str]
    fb_caption: Optional[str]
    li_caption: Optional[str]
    x_caption: Optional[str]

class UpdateStatusRequest(BaseModel):
    row_index: int
    status: str
    platforms: Optional[str] = "all"
    schedule_time: Optional[str] = "now"

class ChatRequest(BaseModel):
    message: str

@app.get("/api/content/pending", response_model=List[ContentRow])
async def get_pending_content():
    try:
        db.connect()
        records = db.content_sheet.get_all_records()
        pending = []
        for i, r in enumerate(records):
            if r.get('status') == 'Draft':
                pending.append(ContentRow(
                    row_index=i+2,
                    topic=r.get('topic', ''),
                    reel_url=r.get('reel_url', ''),
                    status=r.get('status', 'Draft'),
                    platforms=r.get('platforms', 'all'),
                    schedule_time=r.get('schedule_time', 'now'),
                    ig_caption=r.get('ig_caption', ''),
                    fb_caption=r.get('fb_caption', ''),
                    li_caption=r.get('li_caption', ''),
                    x_caption=r.get('x_caption', '')
                ))
        return pending
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/content/approve")
async def approve_content(req: UpdateStatusRequest):
    try:
        db.connect()
        db.content_sheet.update_cell(req.row_index, 9, req.status) # status
        db.content_sheet.update_cell(req.row_index, 7, req.platforms) # platforms
        db.content_sheet.update_cell(req.row_index, 8, req.schedule_time) # schedule_time
        return {"message": f"Row {req.row_index} updated to {req.status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/drive/videos")
async def list_drive_videos():
    try:
        drive.connect()
        videos = drive.list_media()
        return videos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/chat")
async def ai_chat(req: ChatRequest):
    try:
        # 1. Ask Llama to decide which tool to use
        system_prompt = """You are a Social Media Automation Agent.
Your job is to interpret user commands and decide which internal tool to call.
Return a JSON object with 'action' and 'topic' (if needed).
Actions:
- 'research': Scrape news and trends (module1).
- 'generate': Process scraped news into drafts (module2).
- 'publish': Publish approved content (module4).
- 'status': Update/Approve a post (needs row_index).
- 'chat': Just a normal conversational response.

Example Output: {"action": "research", "topic": "AI news"}
Example Output: {"action": "chat", "message": "Hello! How can I help?"}"""

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.message}
            ],
            model="llama3-70b-8192",
            response_format={"type": "json_object"}
        )
        
        intent = json.loads(chat_completion.choices[0].message.content)
        action = intent.get("action")
        
        result_msg = ""
        
        if action == "research":
            # In a real async app we'd use a background task, but for MVP we'll run it synchronously
            run_news_agent() 
            result_msg = "I have finished researching the latest news for you. Check the dashboard!"
        elif action == "generate":
            process_pending_news()
            result_msg = "I've generated new drafts from the news. They are now in the 'Draft' queue."
        elif action == "publish":
            run_publisher()
            result_msg = "I have triggered the publishing engine. Approved posts are going live!"
        elif action == "status":
            result_msg = f"I've received your request to update status. Please confirm the row index if I missed it."
        else:
            result_msg = intent.get("message", "I understand. What's next?")

        return {"response": result_msg, "intent": intent}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
