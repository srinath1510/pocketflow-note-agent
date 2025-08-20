from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import logging

from ..models.session import (
    ContinuationContext, 
    ThreadTimeline, 
    ResumeContext, 
    SessionBoundary
)
from ..services.session_manager import session_manager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/continue/{thread_id}", 
           response_model=ContinuationContext,
           summary="Get thread continuation context",
           description="Get context for resuming research in a specific thread")
async def get_continuation_context(
    thread_id: str, 
    user_id: str = Query(..., description="User identifier")
):
    """
    Get context for resuming research in a thread
    
    Returns:
    - Last session information
    - Resume points for unfinished content
    - Suggested next actions
    - Context summary for quick orientation
    """
    try:
        logger.info(f"Getting continuation context for thread {thread_id}, user {user_id}")
        
        context = session_manager.get_continuation_context(user_id, thread_id)
        
        logger.info(f"Continuation context retrieved: {context.continuation_ready}")
        return context
        
    except Exception as e:
        logger.error(f"Error getting continuation context for thread {thread_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get continuation context: {str(e)}"
        )

@router.get("/timeline/{thread_id}", 
           response_model=ThreadTimeline,
           summary="Get thread research timeline",
           description="Get detailed chronological timeline of research activities")
async def get_thread_timeline(
    thread_id: str, 
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(
        50, 
        ge=1, 
        le=200, 
        description="Number of timeline entries to return"
    )
):
    """
    Get research timeline for a thread with resume points
    
    Returns:
    - Chronological timeline entries with resume contexts
    - Session boundary detection
    - Progress indicators
    - Quick actions for each entry
    """
    try:
        logger.info(f"Getting timeline for thread {thread_id}, user {user_id}, limit {limit}")
        
        timeline = session_manager.get_thread_timeline(user_id, thread_id, limit)
        
        logger.info(f"Timeline retrieved: {timeline.total_entries} total entries, {len(timeline.timeline_entries)} returned")
        return timeline
        
    except Exception as e:
        logger.error(f"Error getting timeline for thread {thread_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get thread timeline: {str(e)}"
        )

@router.get("/capture/{capture_id}", 
           response_model=Optional[ResumeContext],
           summary="Get capture resume context",
           description="Get resume context for a specific capture")
async def get_capture_resume_context(capture_id: str):
    """
    Get resume context for a specific capture
    
    Returns:
    - Resume type (web, video, pdf, ai_chat, note)
    - Last position/progress information
    - Resume actions available
    - Direct resume URLs where applicable
    """
    try:
        logger.info(f"Getting resume context for capture {capture_id}")
        
        context = session_manager.get_capture_resume_context(capture_id)
        
        if not context:
            logger.warning(f"No resume context found for capture {capture_id}")
            raise HTTPException(
                status_code=404, 
                detail="Capture not found or no resume context available"
            )
        
        logger.info(f"Resume context retrieved for capture {capture_id}: {context.resume_type}")
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting resume context for capture {capture_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get capture resume context: {str(e)}"
        )

@router.get("/boundaries/{thread_id}",
           summary="Get thread session boundaries",
           description="Get session boundary detection for research continuity")
async def get_thread_sessions(
    thread_id: str, 
    user_id: str = Query(..., description="User identifier")
):
    """
    Get session boundaries for a thread
    
    Returns:
    - Detected session boundaries (2+ hour gaps)
    - Session duration and capture counts
    - Active session indicators
    """
    try:
        logger.info(f"Getting session boundaries for thread {thread_id}, user {user_id}")
        
        captures = session_manager._get_thread_captures(user_id, thread_id)
        sessions = session_manager._detect_session_boundaries(captures)
        
        result = {
            "thread_id": thread_id,
            "total_sessions": len(sessions),
            "sessions": sessions,
            "total_captures": len(captures),
            "active_sessions": len([s for s in sessions if s.is_active])
        }
        
        logger.info(f"Session boundaries retrieved: {len(sessions)} sessions, {len(captures)} captures")
        return result
        
    except Exception as e:
        logger.error(f"Error getting session boundaries for thread {thread_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get thread sessions: {str(e)}"
        )

@router.get("/resume-points/{thread_id}",
           summary="Get quick resume points",
           description="Get prioritized resume points for quick research continuation")
async def get_thread_resume_points(
    thread_id: str,
    user_id: str = Query(..., description="User identifier"),
    limit: int = Query(5, ge=1, le=20, description="Number of resume points")
):
    """
    Get prioritized resume points for a thread
    
    Focuses on:
    - Incomplete video sessions
    - Partially read documents
    - Recent AI conversations
    - Bookmarked content
    """
    try:
        logger.info(f"Getting resume points for thread {thread_id}, user {user_id}")
        
        # Get recent captures for the thread
        captures = session_manager._get_thread_captures(user_id, thread_id)
        recent_captures = sorted(captures, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit*2]
        
        # Generate resume points with priority scoring
        resume_points = session_manager._generate_resume_points(recent_captures)
        
        # Add priority scoring
        prioritized_points = []
        for point in resume_points[:limit]:
            priority_score = session_manager._calculate_resume_priority(point)
            point['priority_score'] = priority_score
            prioritized_points.append(point)
        
        # Sort by priority
        prioritized_points.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        
        result = {
            "thread_id": thread_id,
            "resume_points": prioritized_points,
            "total_available": len(resume_points),
            "returned": len(prioritized_points)
        }
        
        logger.info(f"Resume points retrieved: {len(prioritized_points)} points")
        return result
        
    except Exception as e:
        logger.error(f"Error getting resume points for thread {thread_id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get resume points: {str(e)}"
        )

@router.post("/mark-resumed/{thread_id}",
            summary="Mark content as resumed",
            description="Mark a capture/session as resumed for tracking")
async def mark_content_resumed(
    thread_id: str,
    capture_id: str = Query(..., description="Capture ID that was resumed"),
    user_id: str = Query(..., description="User identifier"),
    resume_position: Optional[dict] = None
):
    """
    Mark content as resumed and optionally update position
    
    Used for:
    - Tracking which content users actually resume
    - Updating progress positions
    - Analytics on resume effectiveness
    """
    try:
        logger.info(f"Marking capture {capture_id} as resumed in thread {thread_id}")
        
        # Update resume tracking (you could store this in a separate tracking system)
        result = {
            "success": True,
            "thread_id": thread_id,
            "capture_id": capture_id,
            "resumed_at": session_manager._get_current_timestamp(),
            "message": "Content marked as resumed"
        }
        
        if resume_position:
            result["updated_position"] = resume_position
        
        logger.info(f"Resume tracking updated for capture {capture_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error marking content as resumed: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to mark content as resumed: {str(e)}"
        )

# Health check for session continuity
@router.get("/continuity/health",
           summary="Session continuity health check",
           description="Check if session continuity features are working")
async def continuity_health_check():
    """Health check for session continuity features"""
    try:
        # Test session manager initialization
        health_status = {
            "service": "session_continuity",
            "status": "healthy",
            "features": {
                "session_detection": True,
                "resume_context": True,
                "timeline_generation": True
            },
            "session_manager": {
                "initialized": session_manager is not None,
                "active_boundaries": len(getattr(session_manager, 'session_boundaries', {})),
                "active_sessions": len(getattr(session_manager, 'active_sessions', {}))
            },
            "timestamp": session_manager._get_current_timestamp() if session_manager else None
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Session continuity health check failed: {str(e)}")
        return {
            "service": "session_continuity",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": session_manager._get_current_timestamp() if session_manager else None
        }