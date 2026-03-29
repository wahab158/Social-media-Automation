from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import db_content_helper as dbcontent
from auth_helper import get_current_user

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

class RescheduleRequest(BaseModel):
    post_id: str
    new_time: str

@router.get("")
async def get_calendar_posts(start: str, end: str, brand_id: str, user_id: str = Depends(get_current_user)):
    """Fetch all posts for a date range and brand."""
    try:
        posts = dbcontent.get_posts_by_range(brand_id, start, end)
        return {"status": "success", "posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/reschedule")
async def reschedule_post(req: RescheduleRequest, user_id: str = Depends(get_current_user)):
    """Update the scheduled_time for a post (version is incremented in DB logic)."""
    try:
        # Simple update logic for now
        conn = dbcontent.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE posts SET scheduled_time = ?, version = version + 1 WHERE id = ?", (req.new_time, req.post_id))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Post rescheduled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve-week")
async def approve_week(brand_id: str, user_id: str = Depends(get_current_user)):
    """Bulk approve all 'generated' posts for a brand."""
    try:
        conn = dbcontent.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE posts SET status = 'approved' WHERE brand_id = ? AND status = 'generated'", (brand_id,))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Weekly batch approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
