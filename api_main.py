from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

from db_helper import DBHelper
from drive_helper import DriveHelper

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
        # In a real app, we'd update specific columns. 
        # Using db_helper's logic but adapted for more fields
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
        videos = drive.list_videos()
        return videos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
