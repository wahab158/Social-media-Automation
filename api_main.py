from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator
import asyncio
import os
import json
import uuid
from datetime import datetime, timedelta
import threading
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Auth dependencies
from jose import jwt, JWTError
from bcrypt import hashpw, checkpw, gensalt

from db_helper import DBHelper
from cloudinary_helper import CloudinaryHelper, generate_platform_transforms, generate_single_transform

# Module Imports for tool-calling
from module1_news import run_news_agent
from module2_content import process_pending_news_auto, generate_captions, generate_from_single_news, generate_custom_post, get_groq_client
from module4_publisher import run_publisher, publish_single
from vision_helper import analyze_image_with_vision, recommend_ratios
import re
import httpx

# SQLite helpers
from sqlite_helper import (
    init_db, create_user, get_user_by_email, get_user_by_id, update_last_login,
    save_api_key as sqlite_save_key, get_api_key as sqlite_get_key,
    get_all_keys_masked, mark_key_verified, delete_api_key as sqlite_delete_key,
    get_user_settings, save_user_settings, get_connection
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init SQLite on startup
    init_db()
    
    # Connect to Google Sheets in a thread to avoid blocking the event loop
    def connect_db():
        try:
            print(f"[{datetime.now()}] Initializing Google Sheets connection...")
            db.connect()
            print(f"[{datetime.now()}] Google Sheets connected successfully.")
        except Exception as e:
            print(f"[{datetime.now()}] Google Sheets connection failed (server will still run): {e}")

    threading.Thread(target=connect_db, daemon=True).start()
    
    # Start background scheduler
    threading.Thread(target=scheduler_task, daemon=True).start()
    
    yield
    # Cleanup if needed

app = FastAPI(title="Social Media Automation Dashboard API", lifespan=lifespan)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DBHelper()
# Connection moved to lifespan

cloudinary_h = CloudinaryHelper()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

import traceback

def scheduler_task():
    """Background loop that runs every 60 seconds to check against multi-tenant schedules."""
    last_trigger_min = ""
    log_file = "scheduler.log"
    
    def log_msg(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output = f"[{timestamp}] {msg}"
        with open(log_file, "a") as f:
            f.write(output + "\n")
        print(output)

    log_msg("Background scheduler started and monitoring preferences.")

    while True:
        now = datetime.now()
        current_hm = now.strftime("%H:%M")
        
        # Don't run multiple times in the same minute
        if current_hm == last_trigger_min:
            time.sleep(30)
            continue

        try:
            conn = get_connection()
            # Fetch all user settings, but only if they have automated news enabled
            rows = conn.execute("SELECT user_id, post_time, topics FROM user_settings WHERE is_enabled = 1").fetchall()
            conn.close()
            
            for r in rows:
                uid = r['user_id']
                pref_time = r['post_time']
                topics = r['topics']
                
                # Check for schedule match
                if current_hm == pref_time:
                    log_msg(f"Target match! Triggering news agent for user {uid} at {current_hm}")
                    last_trigger_min = current_hm
                    
                    # Run in a separate thread to avoid blocking the scheduler loop
                    def run_async_agent(q, u):
                        try:
                            # run_news_agent creates its own DBHelper instance internally
                            run_news_agent(custom_query=q, user_id=u)
                            log_msg(f"SUCCESS: News agent finished for user {u}")
                        except Exception as ex:
                            log_msg(f"CRITICAL ERROR in news agent for user {u}: {ex}\n{traceback.format_exc()}")

                    t = threading.Thread(target=run_async_agent, args=(topics, uid), daemon=True)
                    t.start()
                    
        except Exception as e:
            log_msg(f"SCHEDULER LOOP ERROR: {e}\n{traceback.format_exc()}")
            
        # Sleep for 30 seconds to re-check
        time.sleep(30)

# Scheduler start moved to lifespan

# ---------- JWT Auth ----------

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 72
security = HTTPBearer(auto_error=False)


def create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[str]:
    """Returns user_id from JWT token or None if no auth provided."""
    if not credentials:
        return None
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ---------- Models ----------

class ContentRow(BaseModel):
    row_index: int
    topic: str
    reel_url: str
    status: str
    platforms: str
    schedule_time: str
    ig_caption: Optional[str] = ""
    fb_caption: Optional[str] = ""
    li_caption: Optional[str] = ""
    x_caption: Optional[str] = ""
    posted_at: Optional[str] = ""

class UpdateStatusRequest(BaseModel):
    row_index: int
    status: str
    platforms: Optional[str] = "all"
    schedule_time: Optional[str] = "now"

class ApprovePublishRequest(BaseModel):
    row_index: int
    platforms: str = "ig,fb,li,rd"
    schedule_time: str = "now"

class EditContentRequest(BaseModel):
    row_index: int
    ig_caption: Optional[str] = None
    fb_caption: Optional[str] = None
    li_caption: Optional[str] = None
    x_caption: Optional[str] = None
    platforms: Optional[str] = None
    reel_url: Optional[str] = None

class RetransformRequest(BaseModel):
    public_id: str
    ratio_key: str

class AIChatRequest(BaseModel):
    message: str

class GenerateNewsRequest(BaseModel):
    news_ids: List[str]  # Supports bulk generation

class FetchNewsRequest(BaseModel):
    topics: Optional[str] = None

class CustomNewsRequest(BaseModel):
    text: str

class SkipNewsRequest(BaseModel):
    news_id: str

class UpdateNewsRequest(BaseModel):
    news_id: str
    summary: Optional[str] = None
    media_url: Optional[str] = None

class RefineCaptionRequest(BaseModel):
    caption: str
    instruction: str
    platform: str

# ---------- Content Endpoints ----------

@app.get("/api/content/pending", response_model=List[ContentRow])
async def get_pending_content(user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        db.connect()
        records = db.content_sheet.get_all_records()
        pending = []
        for i, r in enumerate(records):
            # Show if: 1. It belongs to the current user OR 2. It has no user_id (legacy)
            raw_owner = str(r.get('user_id', '')).strip()
            # Handle 'None' string that might have been accidentally inserted
            owner_id = None if raw_owner in ['', 'None', 'undefined'] else raw_owner
            
            if owner_id and owner_id != user_id:
                continue
                
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
        # Reverse to show newest first
        return pending[::-1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/content/history", response_model=List[ContentRow])
async def get_content_history(user_id: str = Depends(get_current_user)):
    """Returns Posted and Failed content items."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        records = db.content_sheet.get_all_records()
        items = []
        for i, r in enumerate(records):
            owner_id = str(r.get('user_id', '')).strip()
            if owner_id and owner_id != user_id:
                continue

            if r.get('status') in ['Posted', 'Failed', 'Rejected', 'Approved']:
                items.append(ContentRow(
                    row_index=i+2,
                    topic=r.get('topic', ''),
                    reel_url=r.get('reel_url', ''),
                    status=r.get('status', ''),
                    platforms=r.get('platforms', ''),
                    schedule_time=r.get('schedule_time', ''),
                    ig_caption=r.get('ig_caption', ''),
                    fb_caption=r.get('fb_caption', ''),
                    li_caption=r.get('li_caption', ''),
                    x_caption=r.get('x_caption', ''),
                    posted_at=str(r.get('posted_at', ''))
                ))
        return items[::-1]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/content/approve")
async def approve_content(req: UpdateStatusRequest, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        db.content_sheet.update_cell(req.row_index, 9, req.status)
        db.content_sheet.update_cell(req.row_index, 7, req.platforms)
        db.content_sheet.update_cell(req.row_index, 8, req.schedule_time)
        return {"message": f"Row {req.row_index} updated to {req.status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/content/edit")
async def edit_content(req: EditContentRequest, user_id: str = Depends(get_current_user)):
    """Save edited captions and platform selections for a draft."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        if req.ig_caption is not None:
            db.content_sheet.update_cell(req.row_index, 3, req.ig_caption)
        if req.fb_caption is not None:
            db.content_sheet.update_cell(req.row_index, 4, req.fb_caption)
        if req.li_caption is not None:
            db.content_sheet.update_cell(req.row_index, 5, req.li_caption)
        if req.x_caption is not None:
            db.content_sheet.update_cell(req.row_index, 6, req.x_caption)
        if req.platforms is not None:
            db.content_sheet.update_cell(req.row_index, 7, req.platforms)
        if req.reel_url is not None:
            db.content_sheet.update_cell(req.row_index, 2, req.reel_url)
        return {"message": f"Row {req.row_index} updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflow/approve-and-publish")
async def approve_and_publish(req: ApprovePublishRequest, user_id: str = Depends(get_current_user)):
    """Approve a draft and immediately publish it."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # 1. Mark as Approved
        db.content_sheet.update_cell(req.row_index, 9, "Approved")
        db.content_sheet.update_cell(req.row_index, 7, req.platforms)
        db.content_sheet.update_cell(req.row_index, 8, req.schedule_time)
        
        # 2. Publish immediately (Note: publish_single needs user_id if it uses user keys)
        result = publish_single(req.row_index, user_id=user_id)
        return {"message": "Published successfully", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/content/{row_index}")
async def delete_content(row_index: int, user_id: str = Depends(get_current_user)):
    """Delete a content row by clearing its data."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # Mark as Deleted (don't actually remove the row to preserve indices)
        db.content_sheet.update_cell(row_index, 9, "Deleted")
        return {"message": f"Row {row_index} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- News Endpoints ----------

@app.get("/api/news")
async def get_news(user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        # Front end wants all news to filter New / Used / Skipped
        all_news = db.get_all_news()
        return all_news[::-1]
    except Exception as e:
        print(f"Get news error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news/fetch")
async def fetch_news_on_demand(req: FetchNewsRequest, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        count, msg = run_news_agent(custom_query=req.topics, user_id=user_id)
        if count == 0 and "No news found" in msg:
            raise HTTPException(status_code=404, detail="No news found for topic or source unavailable.")
        return {"success": True, "count": count, "message": msg}
    except Exception as e:
        print(f"Fetch news error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news/generate")
async def generate_from_news(req: GenerateNewsRequest, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    results = []
    errors = []
    
    for nid in req.news_ids:
        res = generate_from_single_news(user_id, nid)
        if res.get("success"):
            results.append(res)
        else:
            errors.append(f"Failed for {nid}: {res.get('error')}")
            
    if not results and errors:
        raise HTTPException(status_code=500, detail=" | ".join(errors))
        
    return {"success": True, "generated": len(results), "errors": errors}

@app.post("/api/news/skip")
async def skip_news_item(req: SkipNewsRequest, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        success = db.update_news_status_by_id(req.news_id, "Skipped")
        if not success:
            raise HTTPException(status_code=404, detail="News item not found")
        return {"success": True, "message": "Marked as Skipped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news/edit")
async def edit_news_item(req: UpdateNewsRequest, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = {}
        if req.summary is not None: data['summary'] = req.summary
        if req.media_url is not None: data['media_url'] = req.media_url
        
        success = db.update_news_item(req.news_id, data)
        if not success:
            raise HTTPException(status_code=404, detail="News item not found")
        return {"success": True, "message": "News item updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/news/custom")
async def create_custom_news_post(req: CustomNewsRequest, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        if not req.text or not req.text.strip():
             raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        res = generate_custom_post(user_id, req.text)
        if res.get("success"):
            return {"success": True, "message": "Custom post generated successfully", "data": res}
        else:
             raise HTTPException(status_code=500, detail=res.get("error"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Media Endpoints ----------

@app.post("/api/media/upload")
async def upload_media(file: UploadFile = File(...)):
    try:
        import cloudinary.uploader as cl_uploader
        content = await file.read()
        result = cl_uploader.upload(content, folder="dashboard_uploads", resource_type="auto")
        return {
            "message": "File uploaded successfully",
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "resource_type": result.get("resource_type")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/media/upload-and-analyze")
async def upload_and_analyze(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    """
    Single endpoint that:
    1. Uploads to Cloudinary
    2. Generates all platform transformation URLs
    3. Runs Vision AI ratio recommendation
    Returns everything the Approval Card needs.
    """
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        import cloudinary.uploader as cl_uploader
        contents = await file.read()
        upload_result = cl_uploader.upload(
            contents,
            folder="social_automation/originals",
            resource_type="image",
        )
        public_id = upload_result["public_id"]
        original_url = upload_result["secure_url"]
 
        # Run transforms and AI analysis in parallel
        transform_task = asyncio.to_thread(generate_platform_transforms, public_id)
        vision_task = asyncio.to_thread(recommend_ratios, original_url, user_id=user_id)
        transform_urls, ai_recommendations = await asyncio.gather(
            transform_task, vision_task
        )
 
        return {
            "success": True,
            "public_id": public_id,
            "original_url": original_url,
            "resource_type": upload_result.get("resource_type", "image"),
            "transforms": transform_urls,
            "ai_recommendations": ai_recommendations,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/media/retransform")
async def retransform(req: RetransformRequest):
    """Generate a single new transformed URL when user overrides the AI ratio."""
    try:
        url = generate_single_transform(req.public_id, req.ratio_key)
        return {"url": url, "ratio_key": req.ratio_key}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/media/list")
async def list_media_assets():
    try:
        cl_assets = cloudinary_h.list_assets()
        return {"cloudinary": cl_assets, "drive": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/media/{public_id:path}")
async def delete_media_asset(public_id: str):
    try:
        result = cloudinary_h.delete_asset(public_id)
        if result.get("success"):
            return {"message": f"Deleted {public_id}"}
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Delete failed"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/media/refine-caption")
async def refine_caption(req: RefineCaptionRequest, user_id: str = Depends(get_current_user)):
    """Use AI to refine a social media caption based on instructions."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    prompt = (
        f"You are a social media expert. Refine the following caption for {req.platform}.\n"
        f"Original Caption: {req.caption}\n"
        f"Instruction: {req.instruction}\n\n"
        "Return ONLY the refined caption, no and other text or explanations."
    )
    
    try:
        user_client = get_groq_client(user_id)
        if not user_client:
             raise HTTPException(status_code=500, detail="Groq client could not be initialized. Check API keys.")
        
        response = user_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        refined = response.choices[0].message.content.strip()
        # Strip quotes if the AI added them
        if (refined.startswith('"') and refined.endswith('"')) or (refined.startswith("'") and refined.endswith("'")):
            refined = refined[1:-1]
            
        return {"success": True, "refined": refined}
    except Exception as e:
        print(f"Refine caption error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- AI Chat ----------

    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    async def event_generator():
        try:
            # Ensure user_id is a valid UUID/ID and not 'None' string
            if user_id in [None, 'None', 'undefined', '']:
                yield "data: " + json.dumps({"error": "Invalid user session. Please re-login."}) + "\n\n"
                return

            cl_assets = cloudinary_h.list_assets()
            recent_assets = ", ".join([a['name'] for a in cl_assets[:5]]) if cl_assets else "None"

            # 1. Fetch Post History for Memory
            history_records = db.content_sheet.get_all_records()
            posted_history = [r for r in history_records if r.get('status') == 'Posted'][-5:]
            history_summary = ""
            for h in posted_history:
                history_summary += f"- {h.get('topic')}: {h.get('ig_caption')[:100]}...\n"

            if not history_summary:
                history_summary = "None yet."

            # 2. Regex interception for Vision Analysis
            image_url = None
            vision_context = ""
            current_topic = "General Interest"
            
            yield "data: " + json.dumps({"status": "Analyzing your request..."}) + "\n\n"
            
            match = re.search(r'\[Pinned Image: ".*" — (https?://[^\]]+)\]', req.message)
            if match:
                image_url = match.group(1)
                yield "data: " + json.dumps({"status": "Analyzing image with Vision AI..."}) + "\n\n"
                raw_vision = analyze_image_with_vision(image_url, user_id=user_id)
                try:
                    v_data = json.loads(raw_vision)
                    vision_context = (
                        f"VISUAL DATA FROM IMAGE:\n"
                        f"- BUSINESS/ENTITY: {v_data.get('business_name', 'Not explicitly mentioned')}\n"
                        f"- CORE VISUALS: {v_data.get('visual_description', 'N/A')}\n"
                        f"- VISIBLE TEXT SNIPPETS: {v_data.get('extracted_text', 'None found')[:500]} (truncated)\n"
                        f"- DETAILS FOUND: {v_data.get('contact_info', 'None')}.\n"
                        f"\nImportant: We are creating a social media post about this image. Treat these visual details as if you are seeing them yourself. Do not mention technical vision analysis."
                    )
                    # Infer a better topic: use business name + some extracted text
                    biz = v_data.get('business_name', '').strip()
                    txt = v_data.get('extracted_text', '').strip()
                    if biz and txt:
                        current_topic = f"{biz}: {txt[:60]}..."
                    else:
                        current_topic = biz or txt[:100] or "General Interest"
                    vision_confidence = v_data.get('confidence_score', 0)
                except Exception as e:
                    print(f"Vision parse error: {e}")
                    vision_context = f"\n[VISION ANALYSIS]: {raw_vision}\n"
                    current_topic = "General Interest"
                    vision_confidence = 100

            # Initialize Groq client with user key
            user_client = get_groq_client(user_id)
            if not user_client:
                yield "data: " + json.dumps({"error": "No AI configuration found. Please add your Groq key in Settings."}) + "\n\n"
                return

            system_prompt = f"""You are Antigravity, an AI Social Media Co-Pilot.

RULES:
1. NEVER run research blindly. If the user says "find news" or "research", ASK "What topic?" unless they already specified one.
2. When the user has a pinned image (shown as [Pinned Image:...]), acknowledge it and use it for any content you generate.
3. Always be conversational, helpful, and concise.
4. Only use 'research' action when user provides a clear topic.
5. IF the vision analysis has low confidence (< 70%) or mentions uncertainty/blurry text, you MUST ask the user to clarify those specific details instead of generating a post.
6. IF the user wants a post for the image and the analysis is clear, output "action": "auto_pipeline" and generate a "topic" that includes the Business Name and the core offer.

Context:
- Recent Cloudinary Assets: {recent_assets}
- Recent Post History (Avoid Repeating!):
{history_summary}
{vision_context}

Return JSON:
- "action": "research" | "generate" | "publish" | "auto_pipeline" | "chat"  
- "topic": specific research topic (only if user provided one, or inferred from image)
- "message": your response to the user  
- "requires_confirm": true if waiting for user input

Examples:
No topic: {{"action": "chat", "message": "I'd love to help! What specific topic should I research?", "requires_confirm": true}}
Has topic: {{"action": "research", "topic": "AI Stocks", "message": "Researching AI Stocks now..."}}
"""

            chat_completion = user_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req.message}
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            
            intent = json.loads(chat_completion.choices[0].message.content)
            action = intent.get("action")
            result_msg = intent.get("message", "I understand.")
            
            if action == "research":
                topic = intent.get("topic")
                if topic:
                    yield "data: " + json.dumps({"status": f"Searching for '{topic}'..."}) + "\n\n"
                    run_news_agent(custom_query=topic, user_id=user_id)
                    if not intent.get("message"):
                        result_msg = f"Research on '{topic}' complete!"
                else:
                    result_msg = "What topic should I research for you?"
                    intent["action"] = "chat"
            elif action == "generate":
                yield "data: " + json.dumps({"status": "Generating social media magic..."}) + "\n\n"
                count, new_indices, first_draft = process_pending_news_auto(media_url=image_url, user_id=user_id)
                # Use local data for preview to avoid network lag/errors
                if first_draft:
                    intent["draft_preview"] = first_draft
                elif new_indices:
                    # Fallback if first_draft is missing but indices exist
                    try:
                        target_row = new_indices[0]
                        record = db.content_sheet.row_values(target_row)
                        intent["draft_preview"] = {
                            "topic": record[0],
                            "caption": record[3],
                            "row_index": target_row
                        }
                    except Exception as e:
                        print(f"Preview fetch fallback error: {e}")

                if not intent.get("message"):
                    result_msg = "Drafts generated! Please review them."
                    
            elif action == "publish":
                yield "data: " + json.dumps({"status": "Sending your post to the world..."}) + "\n\n"
                run_publisher(user_id=user_id)
                if not intent.get("message"):
                    result_msg = "Publishing engine started."
                    
            elif action == "auto_pipeline":
                topic = intent.get("topic", "New Content")
                yield "data: " + json.dumps({"status": f"Crafting post for '{topic}'..."}) + "\n\n"
                
                # NO LONGER RESEARCHING INTERNET. Generate directly.
                try:
                    yield "data: " + json.dumps({"status": "Generating AI captions..."}) + "\n\n"
                    # Pass vision context if available to make it relevant to the image
                    context_for_ai = f"User Intent: {req.message}\nVisual Context: {vision_context}"
                    caps = generate_captions(topic, context_for_ai, user_client)
                    
                    new_idx = db.add_content_row(
                        topic=topic,
                        reel_url=image_url or "",
                        ig_caption=caps.get("ig", ""),
                        fb_caption=caps.get("fb", ""),
                        li_caption=caps.get("li", ""),
                        x_caption=caps.get("x", ""),
                        platforms="all",
                        schedule_time="now",
                        status="Draft",
                        user_id=user_id
                    )
                    
                    intent["action"] = "generate"
                    intent["draft_preview"] = {
                        "topic": topic,
                        "caption": caps.get("ig", ""),
                        "row_index": new_idx
                    }
                    
                    if not intent.get("message"):
                        result_msg = f"Draft created for '{topic}'! You can edit or publish it now."
                        
                except Exception as e:
                    print(f"Auto-Pipeline direct generation error: {e}")
                    yield "data: " + json.dumps({"error": f"Failed to generate draft: {str(e)}"}) + "\n\n"
                    return

            # Send final response
            yield "data: " + json.dumps({
                "message": result_msg,
                "action": intent.get("action", "chat"),
                "draft_preview": intent.get("draft_preview")
            }) + "\n\n"

        except Exception as e:
            print(f"AI Chat Error: {e}")
            yield "data: " + json.dumps({"error": str(e)}) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ---------- Auth Routes ----------

@app.post("/api/auth/register")
async def register(payload: dict):
    email = payload.get("email", "").lower().strip()
    password = payload.get("password", "")
    name = payload.get("name", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hashpw(password.encode(), gensalt()).decode()
    user_id = str(uuid.uuid4())

    create_user({
        "id": user_id,
        "email": email,
        "password": hashed,
        "name": name,
        "created_at": datetime.utcnow().isoformat(),
    })

    return {"token": create_token(user_id), "user_id": user_id, "email": email}


@app.post("/api/auth/login")
async def login(payload: dict):
    email = payload.get("email", "").lower().strip()
    password = payload.get("password", "")

    user = get_user_by_email(email)
    if not user or not checkpw(password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    update_last_login(user["id"])
    return {"token": create_token(user["id"]), "user_id": user["id"], "email": user["email"]}


@app.get("/api/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


# ---------- Settings Routes ----------

@app.get("/api/settings")
async def get_settings(user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    keys = get_all_keys_masked(user_id)
    prefs = get_user_settings(user_id)
    return {"keys": keys, "preferences": prefs}


@app.post("/api/settings/keys")
async def save_key(payload: dict, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    service = payload.get("service")
    key_name = payload.get("key_name")
    value = payload.get("value")
    if not all([service, key_name, value]):
        raise HTTPException(status_code=400, detail="service, key_name, value required")
    sqlite_save_key(user_id, service, key_name, value)
    return {"status": "saved", "service": service, "key_name": key_name}


@app.delete("/api/settings/keys")
async def remove_key(payload: dict, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sqlite_delete_key(user_id, payload["service"], payload["key_name"])
    return {"status": "deleted"}


@app.post("/api/settings/preferences")
async def save_preferences(payload: dict, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    save_user_settings(user_id, payload)
    return {"status": "saved"}


@app.post("/api/settings/test/{service}")
async def test_connection(service: str, user_id: str = Depends(get_current_user)):
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    testers = {
        "openai": _test_openai,
        "groq": _test_groq,
        "ayrshare": _test_ayrshare,
        "cloudinary": _test_cloudinary,
        "newsapi": _test_newsapi,
        "tavily": _test_tavily,
        "sheets": _test_sheets,
    }
    tester = testers.get(service)
    if not tester:
        raise HTTPException(status_code=400, detail=f"Unknown service: {service}")
    return await tester(user_id)


# ---------- Test Connection Functions ----------

async def _test_openai(user_id: str) -> dict:
    key = sqlite_get_key(user_id, "openai", "api_key")
    if not key:
        return {"success": False, "error": "No OpenAI key saved"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://api.openai.com/v1/models",
                           headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if r.status_code == 200:
            mark_key_verified(user_id, "openai", "api_key")
            return {"success": True, "message": "OpenAI connected successfully"}
        return {"success": False, "error": f"OpenAI returned {r.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_groq(user_id: str) -> dict:
    key = sqlite_get_key(user_id, "groq", "api_key")
    if not key:
        return {"success": False, "error": "No Groq key saved"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://api.groq.com/openai/v1/models",
                           headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if r.status_code == 200:
            mark_key_verified(user_id, "groq", "api_key")
            return {"success": True, "message": "Groq connected successfully"}
        return {"success": False, "error": f"Groq returned {r.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_ayrshare(user_id: str) -> dict:
    key = sqlite_get_key(user_id, "ayrshare", "api_key")
    if not key:
        return {"success": False, "error": "No Ayrshare key saved"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://api.ayrshare.com/api/user",
                           headers={"Authorization": f"Bearer {key}"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            platforms = data.get("activeSocialAccounts", [])
            mark_key_verified(user_id, "ayrshare", "api_key")
            sqlite_save_key(user_id, "ayrshare", "connected_platforms", ",".join(platforms))
            return {"success": True, "connected_platforms": platforms,
                    "display_name": data.get("displayName", "")}
        return {"success": False, "error": "Invalid Ayrshare key"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_cloudinary(user_id: str) -> dict:
    cloud_name = sqlite_get_key(user_id, "cloudinary", "cloud_name")
    api_key = sqlite_get_key(user_id, "cloudinary", "api_key")
    api_secret = sqlite_get_key(user_id, "cloudinary", "api_secret")
    if not all([cloud_name, api_key, api_secret]):
        return {"success": False, "error": "Cloud name, API key, and secret required"}
    try:
        import cloudinary as cl_lib
        cl_lib.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)
        cl_lib.api.ping()
        mark_key_verified(user_id, "cloudinary", "api_key")
        return {"success": True, "message": "Cloudinary connected successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_newsapi(user_id: str) -> dict:
    key = sqlite_get_key(user_id, "newsapi", "api_key")
    if not key:
        return {"success": False, "error": "No NewsAPI key saved"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("https://newsapi.org/v2/top-headlines",
                           params={"country": "us", "pageSize": 1, "apiKey": key}, timeout=10)
        if r.status_code == 200:
            mark_key_verified(user_id, "newsapi", "api_key")
            return {"success": True, "message": "NewsAPI connected successfully"}
        return {"success": False, "error": f"NewsAPI returned {r.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_tavily(user_id: str) -> dict:
    key = sqlite_get_key(user_id, "tavily", "api_key")
    if not key:
        return {"success": False, "error": "No Tavily key saved"}
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api.tavily.com/search",
                            json={"api_key": key, "query": "test", "max_results": 1}, timeout=10)
        if r.status_code == 200:
            mark_key_verified(user_id, "tavily", "api_key")
            return {"success": True, "message": "Tavily connected successfully"}
        return {"success": False, "error": f"Tavily returned {r.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _test_sheets(user_id: str) -> dict:
    sheet_id = sqlite_get_key(user_id, "sheets", "spreadsheet_id")
    sa_json = sqlite_get_key(user_id, "sheets", "service_account_json")
    if not all([sheet_id, sa_json]):
        return {"success": False, "error": "Spreadsheet ID and service account JSON required"}
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(
            json.loads(sa_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        gs_client = gspread.authorize(creds)
        sheet = gs_client.open_by_key(sheet_id)
        tab_names = [ws.title for ws in sheet.worksheets()]
        mark_key_verified(user_id, "sheets", "spreadsheet_id")
        return {"success": True, "message": f"Connected. Tabs: {', '.join(tab_names)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
