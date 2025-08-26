"""
Thread management endpoints (/api/v1/threads)
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import logging

from ..models.thread import (
    ResearchThread, ThreadSwitchRequest, ThreadCreateRequest, 
    ThreadUpdateRequest, ThreadsResponse, ThreadSwitchResponse
)
from ..services.thread_manager import thread_manager
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{user_id}", response_model=ThreadsResponse)
async def get_user_threads(user_id: str):
    """Get all research threads for a user"""
    try:
        threads = thread_manager.get_user_threads(user_id)
        active_thread = thread_manager.get_active_thread(user_id)
        
        # Calculate status counts
        status_counts = {"active": 0, "paused": 0, "completed": 0, "archived": 0}
        for thread in threads:
            status_counts[thread.status] += 1
        
        return ThreadsResponse(
            threads=threads,
            active_thread=active_thread,
            total_count=len(threads),
            by_status=status_counts
        )
    except Exception as e:
        logger.error(f"Error getting threads for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch", response_model=ThreadSwitchResponse)
async def switch_thread_context(request: ThreadSwitchRequest):
    """Switch between research threads"""
    try:
        result = thread_manager.switch_context(request)
        
        return ThreadSwitchResponse(
            success=True,
            from_thread=result["from_thread"],
            to_thread=result["to_thread"],
            context_summary=result["context_summary"],
            switch_timestamp=datetime.now(timezone.utc).isoformat()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error switching thread context: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=ResearchThread)
async def create_thread(request: ThreadCreateRequest):
    """Create new research thread"""
    try:
        # Validate thread name
        if not request.name or len(request.name.strip()) < 2:
            raise HTTPException(status_code=400, detail="Thread name must be at least 2 characters")
        
        thread = thread_manager.create_thread(request)
        return thread
    except Exception as e:
        logger.error(f"Error creating thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}/{thread_id}", response_model=ResearchThread)
async def update_thread(user_id: str, thread_id: str, update: ThreadUpdateRequest):
    """Update research thread"""
    try:
        thread = thread_manager.update_thread(user_id, thread_id, update)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        return thread
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}/{thread_id}")
async def delete_thread(user_id: str, thread_id: str):
    """Delete research thread"""
    try:
        success = thread_manager.delete_thread(user_id, thread_id)
        if not success:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        return {
            "success": True,
            "message": f"Thread {thread_id} deleted",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/active", response_model=Optional[ResearchThread])
async def get_active_thread(user_id: str):
    """Get user's currently active thread"""
    try:
        active_thread = thread_manager.get_active_thread(user_id)
        return active_thread
    except Exception as e:
        logger.error(f"Error getting active thread: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))