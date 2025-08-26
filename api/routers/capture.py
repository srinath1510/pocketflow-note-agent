"""
Capture endpoints (/api/v1/capture)
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import uuid
import time
import logging
import traceback

from ..models.capture import UniversalCaptureRequest, UniversalCaptureResponse, ThreadAssignment, TimelineEntry, MinimalInsight
from ..services.content_processor import content_processor
from ..services.rate_limiter import rate_limiter
from ..services.thread_manager import thread_manager
from ..utils.storage import notes_storage, active_threads

logger = logging.getLogger(__name__)
router = APIRouter()


async def check_rate_limit(request: Request, capture_request: UniversalCaptureRequest) -> UniversalCaptureRequest:
    """
    Rate limiting dependency for capture endpoints
    
    Raises HTTPException if rate limit exceeded
    """
    user_id = capture_request.user_id
    allowed, rate_info = rate_limiter.is_allowed(user_id)
    
    if not allowed:
        # Add rate limit headers to the exception
        headers = {
            "X-RateLimit-Limit": str(rate_info['limit']),
            "X-RateLimit-Remaining": str(rate_info['remaining']),
            "X-RateLimit-Reset": str(int(rate_info['reset_time'])),
            "Retry-After": str(int(rate_info['reset_time'] - time.time()))
        }
        
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {rate_info['limit']} requests per {rate_info['window_seconds']} seconds",
                "rate_limit": rate_info,
                "retry_after_seconds": int(rate_info['reset_time'] - time.time())
            },
            headers=headers
        )
    
    # Add rate limit info to request headers for successful requests
    if hasattr(request, 'state'):
        request.state.rate_limit_info = rate_info
    
    return capture_request


@router.post("/", response_model=UniversalCaptureResponse)
async def process_universal_capture(
    request: Request,
    capture_request: UniversalCaptureRequest = Depends(check_rate_limit)
):
    """
    Universal capture endpoint supporting all content types with rate limiting
    
    Rate Limits:
    - 30 requests per minute per user
    - Returns 429 status when exceeded
    - Includes rate limit headers in response
    
    Handles: web content, AI chats, PDF reading, YouTube videos, manual notes
    Returns: thread assignment, timeline entry, and minimal insights
    """
    start_time = time.time()
    
    try:
        logger.info(f"=== UNIVERSAL CAPTURE REQUEST ===")
        logger.info(f"Type: {capture_request.type}")
        logger.info(f"User: {capture_request.user_id}")
        logger.info(f"Content length: {len(capture_request.content)}")
        
        # Generate capture ID
        capture_id = str(uuid.uuid4())
        
        # Process content based on type
        processed_capture = content_processor.process_capture(capture_request)
        
        # Create normalized capture for pipeline
        normalized_capture = {
            'content': capture_request.content,
            'user_id': capture_request.user_id,
            'source_url': capture_request.source_url or 'unknown',
            'title': capture_request.title or 'Untitled',
            'timestamp': capture_request.timestamp or datetime.now(timezone.utc).isoformat(),
            'intent': 'learn',  # Default intent
            'user_note': '',
            'capture_id': capture_id,
            'capture_type': capture_request.type.value,
            'processed_metadata': processed_capture
        }
        
        # Simple thread detection
        thread_assignment = ThreadAssignment(
            thread_id=capture_request.thread_id,
            thread_name=f"Research Thread",
            confidence=0.8,
            assignment_type="suggested",
            suggested_thread_name=f"{capture_request.type.value.replace('_', ' ').title()} Research"
        )

         # If thread_id provided, update thread activity
        if capture_request.thread_id:
            thread_manager.update_thread_activity(
                capture_request.user_id, 
                capture_request.thread_id, 
                capture_added=True
            )
            active_threads[capture_request.user_id] = capture_request.thread_id

        normalized_capture['thread_id'] = capture_request.thread_id

        
        # Create timeline entry
        timeline_entry = TimelineEntry(
            capture_id=capture_id,
            timestamp=normalized_capture['timestamp'],
            capture_type=capture_request.type,
            source_title=capture_request.title or 'Untitled',
            source_url=capture_request.source_url,
            content_preview=capture_request.content[:200] + "..." if len(capture_request.content) > 200 else capture_request.content,
            resume_context=processed_capture.get('resume_context'),
            quick_actions=[
                f"Continue {capture_request.type.value.replace('_', ' ')}",
                "Add to research notes",
                "Share with team"
            ]
        )
        
        # Generate minimal insights (mock for now)
        minimal_insights = [MinimalInsight(
            capture_id=capture_id,
            key_concepts=processed_capture.get('thread_signals', [])[:3],
            actionable_items=processed_capture.get('practical_insights', [])[:2],
            connections=[]
        )]
        
        # Store capture (add to existing storage)
        notes_storage.append(normalized_capture)
        
        processing_time = time.time() - start_time
        
        # Get rate limit info for response headers
        rate_info = getattr(request.state, 'rate_limit_info', {})
        
        logger.info(f"✅ Capture processed successfully")
        logger.info(f"   Capture ID: {capture_id}")
        logger.info(f"   Thread: {thread_assignment.suggested_thread_name}")
        logger.info(f"   Processing time: {processing_time:.3f}s")
        logger.info(f"   Rate limit: {rate_info.get('current_requests', 0)}/{rate_info.get('limit', 30)}")
        
        response = UniversalCaptureResponse(
            success=True,
            capture_id=capture_id,
            thread_assignment=thread_assignment,
            timeline_entry=timeline_entry,
            minimal_insights=minimal_insights,
            next_actions=[
                "Continue research in this thread",
                "Review related captures",
                "Add more context"
            ],
            processing_time=processing_time,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        return response
        
    except HTTPException:
        # Re-raise rate limit and other HTTP exceptions
        raise
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Universal capture error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process capture: {str(e)}"
        )


@router.get("/rate-limit/{user_id}")
async def get_rate_limit_status(user_id: str):
    """Get current rate limit status for a user"""
    try:
        from ..services.rate_limiter import rate_limit_storage
        
        allowed, rate_info = rate_limiter.is_allowed(user_id)
        
        # Don't actually consume a request for this check
        if allowed and rate_limit_storage[user_id]:
            rate_limit_storage[user_id].pop()  # Remove the request we just added
        
        return {
            "user_id": user_id,
            "rate_limit": rate_info,
            "status": "within_limit" if allowed else "rate_limited",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Rate limit status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))