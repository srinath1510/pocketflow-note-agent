"""
Thread-related Pydantic models
"""
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from typing import Literal


class ResearchThread(BaseModel):
    """Research thread model"""
    id: str
    user_id: str
    name: str
    emoji: str = "📚"
    domain: Optional[str] = None
    progress_score: float = 0.0
    created_at: str
    last_active: str
    capture_count: int = 0
    topics: List[str] = []
    status: Literal["active", "paused", "completed", "archived"] = "active"


class ThreadSwitchRequest(BaseModel):
    """Thread context switching request"""
    user_id: str
    from_thread_id: Optional[str] = None
    to_thread_id: str


class ThreadCreateRequest(BaseModel):
    """Thread creation request"""
    user_id: str
    name: str
    emoji: str = "📚"
    domain: Optional[str] = None
    initial_topics: List[str] = []


class ThreadUpdateRequest(BaseModel):
    """Thread update request"""
    name: Optional[str] = None
    emoji: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[Literal["active", "paused", "completed", "archived"]] = None
    topics: Optional[List[str]] = None


class ThreadsResponse(BaseModel):
    """Response for thread listing"""
    threads: List[ResearchThread]
    active_thread: Optional[ResearchThread] = None
    total_count: int
    by_status: Dict[str, int]


class ThreadSwitchResponse(BaseModel):
    """Response for thread switching"""
    success: bool
    from_thread: Optional[ResearchThread] = None
    to_thread: ResearchThread
    context_summary: Dict[str, Any]
    switch_timestamp: str