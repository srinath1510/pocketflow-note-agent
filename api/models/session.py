from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ResumeContext(BaseModel):
    """Resume context for any capture type"""
    resume_type: str  # web, video, pdf, ai_chat, note
    source_url: Optional[str] = None
    last_position: Optional[Dict[str, Any]] = None
    progress_percentage: Optional[float] = None
    user_context: Optional[str] = None
    resume_actions: List[str] = []

class SessionBoundary(BaseModel):
    """Session boundary detection"""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    capture_count: int
    is_active: bool = True

class ContinuationContext(BaseModel):
    """Response for thread continuation"""
    thread_id: str
    continuation_ready: bool
    last_session: Optional[SessionBoundary] = None
    resume_points: List[Dict[str, Any]] = []
    suggested_actions: List[str] = []
    context_summary: str
    next_steps: List[str] = []

class TimelineEntryDetail(BaseModel):
    """Detailed timeline entry with resume capability"""
    capture_id: str
    thread_id: str
    timestamp: str
    capture_type: str
    source_title: str
    source_url: Optional[str] = None
    content_preview: str
    resume_context: Optional[ResumeContext] = None
    session_context: Optional[Dict[str, Any]] = None
    quick_actions: List[str] = []
    related_captures: List[str] = []

class ThreadTimeline(BaseModel):
    """Timeline response for a research thread"""
    thread_id: str
    thread_name: str
    timeline_entries: List[TimelineEntryDetail]
    session_boundaries: List[SessionBoundary]
    total_entries: int
    date_range: Dict[str, str]
    progress_indicators: Dict[str, Any]