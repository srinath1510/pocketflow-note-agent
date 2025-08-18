"""
FastAPI API Server for Smart Notes Extension
Migrated from Flask with async support and automatic documentation
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
import json
import uuid
import logging
import os
import traceback
import sys
import hashlib
import asyncio
from collections import defaultdict
from enum import Enum
from typing import Literal
import time

from pipeline_orchestrator import PipelineOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app with metadata for automatic documentation
app = FastAPI(
    title="Smart Notes API",
    description="""
    AI-powered research continuity assistant that transforms multi-modal captures 
    into organized knowledge with intelligent thread management.
    
    ## Features
    - Multi-modal capture support (web, chat, PDF, YouTube, notes)
    - Research thread detection and management  
    - Session continuity across time
    - Batch LLM processing with optimization
    - Neo4j knowledge graph integration
    - Notion note generation
    
    ## Quick Start
    1. Capture content using POST /api/v1/capture
    2. Trigger AI processing with POST /api/bake
    3. Get results with GET /api/results
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "http://localhost:*",
        "https://localhost:*",
        "http://127.0.0.1:*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Storage directories
NOTES_DIR = Path("data/notes")
BATCHES_DIR = Path("data/batches")
RESULTS_DIR = Path("data/results")

# Create directories
for dir_path in [NOTES_DIR, BATCHES_DIR, RESULTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# In-memory storage
notes_storage = []
batches_storage = []
processing_results = []
processed_batches = set()
processed_bakes = set()
content_hashes = set()
last_bake_time = None
BAKE_THROTTLE_SECONDS = 10

# Initialize pipeline orchestrator
try:
    pipeline_orchestrator = PipelineOrchestrator()
    logger.info("Pipeline orchestrator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pipeline orchestrator: {str(e)}")
    pipeline_orchestrator = None

# Pydantic Models for Request/Response validation

class CaptureMetadata(BaseModel):
    content_category: Optional[str] = "general"
    captured_at: Optional[str] = None
    tags: Optional[List[str]] = []
    local_id: Optional[str] = None

class CaptureSource(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = "Untitled"
    domain: Optional[str] = None

class SingleCapture(BaseModel):
    content: str = Field(..., min_length=1, description="The captured content")
    user_id: str = Field(..., min_length=1, description="User identifier")
    source_url: Optional[str] = Field(None, description="Source URL")
    title: Optional[str] = Field("Untitled", description="Content title")
    timestamp: Optional[str] = Field(None, description="Capture timestamp")
    intent: Optional[str] = Field("learn", description="User intent: learn, research, reference, archive")
    user_note: Optional[str] = Field("", description="User's personal note")
    
    # Legacy support for existing extension
    source: Optional[CaptureSource] = None
    metadata: Optional[CaptureMetadata] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Machine learning is a method of data analysis that automates analytical model building.",
                "user_id": "researcher_123",
                "source_url": "https://example.com/ml-intro",
                "title": "Introduction to Machine Learning",
                "intent": "learn",
                "user_note": "Important for my AI course"
            }
        }
    )

class BatchRequest(BaseModel):
    notes: List[SingleCapture] = Field(..., min_items=1, description="Array of captures to process")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")
    timestamp: Optional[str] = Field(None, description="Batch timestamp")
    processing_mode: Optional[str] = Field("default", description="Processing mode")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "notes": [
                    {
                        "content": "Neural networks are computing systems inspired by biological neural networks.",
                        "user_id": "researcher_123",
                        "source_url": "https://example.com/neural-networks",
                        "title": "Introduction to Neural Networks",
                        "intent": "research"
                    }
                ]
            }
        }
    )

class BakeRequest(BaseModel):
    bake_id: Optional[str] = Field(None, description="Optional bake identifier")
    timestamp: Optional[str] = Field(None, description="Bake timestamp")
    source: Optional[str] = Field("api", description="Trigger source")
    includeAdditionalNotes: Optional[bool] = Field(False, description="Include additional notes")
    additionalNotes: Optional[str] = Field("", description="Additional notes to include")
    trigger_source: Optional[str] = Field("api", description="Legacy trigger source field")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bake_id": "session_123",
                "includeAdditionalNotes": False
            }
        }
    )

class BatchResponse(BaseModel):
    success: bool
    status: str
    batch_id: str
    notes_received: int
    notes_processed: int
    duplicates_filtered: int
    message: str
    timestamp: str

class BakeResponse(BaseModel):
    success: bool
    status: str
    bake_id: str
    message: str
    notes_count: int
    timestamp: str
    data: Dict[str, Any] = {}

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    service: str
    server_type: str
    debug_mode: bool
    endpoints: Dict[str, str]

class PaginationInfo(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool

class NotesResponse(BaseModel):
    notes: List[Dict[str, Any]]
    pagination: PaginationInfo
    stats: Dict[str, Any]
    timestamp: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: str
    error_type: Optional[str] = None
    debug: Optional[str] = None

class CaptureType(str, Enum):
    """Supported capture types for multi-modal content"""
    WEB_CONTENT = "web_content"
    AI_CHAT = "ai_chat"
    PDF_READING = "pdf_reading"
    YOUTUBE_VIDEO = "youtube_video"
    QUICK_NOTE = "quick_note"

class UniversalCaptureRequest(BaseModel):
    """Universal capture request supporting all content types"""
    type: CaptureType = Field(..., description="Type of content being captured")
    content: str = Field(..., min_length=1, description="The captured content")
    user_id: str = Field(..., min_length=1, description="User identifier")
    source_url: Optional[str] = Field(None, description="Source URL if applicable")
    title: Optional[str] = Field("Untitled", description="Content title")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Capture-specific metadata")
    thread_id: Optional[str] = Field(None, description="Research thread assignment")
    timestamp: Optional[str] = Field(None, description="Capture timestamp")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "web_content",
                "content": "Machine learning is a method of data analysis that automates analytical model building.",
                "user_id": "researcher_123",
                "source_url": "https://example.com/ml-intro",
                "title": "Introduction to Machine Learning",
                "metadata": {
                    "reading_time": 5,
                    "scroll_position": 0.75,
                    "highlights": ["analytical model building"]
                }
            }
        }
    )


class ThreadAssignment(BaseModel):
    """Thread assignment information"""
    thread_id: Optional[str] = None
    thread_name: Optional[str] = None
    confidence: float = 0.0
    assignment_type: Literal["existing", "new", "suggested"] = "suggested"
    suggested_thread_name: Optional[str] = None

class TimelineEntry(BaseModel):
    """Timeline entry for research continuity"""
    capture_id: str
    timestamp: str
    capture_type: CaptureType
    source_title: str
    source_url: Optional[str] = None
    content_preview: str
    resume_context: Optional[Dict[str, Any]] = None
    quick_actions: List[str] = []

class MinimalInsight(BaseModel):
    """Minimal, actionable insight"""
    capture_id: str
    key_concepts: List[str] = []
    actionable_items: List[str] = []
    connections: List[str] = []

class UniversalCaptureResponse(BaseModel):
    """Response for universal capture endpoint"""
    success: bool
    capture_id: str
    thread_assignment: ThreadAssignment
    timeline_entry: TimelineEntry
    minimal_insights: List[MinimalInsight] = []
    next_actions: List[str] = []
    processing_time: float
    timestamp: str

# Content type processors class
class ContentTypeProcessor:
    """Process different types of captured content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_capture(self, request: UniversalCaptureRequest) -> Dict[str, Any]:
        """Process capture based on type"""
        processors = {
            CaptureType.WEB_CONTENT: self._process_web_content,
            CaptureType.AI_CHAT: self._process_ai_conversation,
            CaptureType.PDF_READING: self._process_pdf_session,
            CaptureType.YOUTUBE_VIDEO: self._process_video_learning,
            CaptureType.QUICK_NOTE: self._process_manual_note
        }
        
        processor = processors.get(request.type, self._process_web_content)
        return processor(request)
    
    def _process_web_content(self, request: UniversalCaptureRequest) -> Dict[str, Any]:
        """Process web article/content"""
        metadata = request.metadata or {}
        
        return {
            'content_type': 'web_content',
            'processed_content': request.content,
            'source_metadata': {
                'url': request.source_url,
                'title': request.title,
                'domain': self._extract_domain(request.source_url or ''),
                'reading_time': metadata.get('reading_time', 0),
                'scroll_position': metadata.get('scroll_position', 0),
                'highlights': metadata.get('highlights', [])
            },
            'thread_signals': self._extract_topic_keywords(request.content),
            'resume_context': {
                'resume_type': 'web',
                'url': request.source_url,
                'scroll_position': metadata.get('scroll_position', 0),
                'reading_progress': metadata.get('reading_progress', 0)
            }
        }
    
    def _process_ai_conversation(self, request: UniversalCaptureRequest) -> Dict[str, Any]:
        """Process AI chat conversation"""
        metadata = request.metadata or {}
        
        return {
            'content_type': 'ai_conversation',
            'user_questions': self._extract_user_questions(request.content),
            'key_answers': self._extract_key_answers(request.content),
            'practical_insights': self._extract_actionable_items(request.content),
            'conversation_metadata': {
                'platform': metadata.get('platform', 'unknown'),
                'session_length': metadata.get('session_length', 0),
                'conversation_id': metadata.get('conversation_id'),
                'user_satisfaction': metadata.get('user_satisfaction')
            },
            'thread_signals': self._extract_topic_keywords(request.content),
            'resume_context': {
                'resume_type': 'ai_chat',
                'platform': metadata.get('platform'),
                'conversation_url': request.source_url,
                'last_question': self._get_last_user_question(request.content)
            }
        }
    
    def _process_pdf_session(self, request: UniversalCaptureRequest) -> Dict[str, Any]:
        """Process PDF reading session"""
        metadata = request.metadata or {}
        
        return {
            'content_type': 'pdf_reading',
            'document_title': request.title,
            'pages_read': metadata.get('page_range', []),
            'user_highlights': metadata.get('highlights', []),
            'user_annotations': metadata.get('annotations', []),
            'reading_progress': metadata.get('progress_percentage', 0),
            'session_duration': metadata.get('reading_time_minutes', 0),
            'document_metadata': {
                'total_pages': metadata.get('total_pages'),
                'author': metadata.get('author'),
                'publication_date': metadata.get('publication_date'),
                'document_type': metadata.get('document_type', 'pdf')
            },
            'thread_signals': self._extract_topic_keywords(request.content),
            'resume_context': {
                'resume_type': 'pdf',
                'document_url': request.source_url,
                'last_page': metadata.get('last_page_read'),
                'reading_progress': metadata.get('progress_percentage', 0)
            }
        }
    
    def _process_video_learning(self, request: UniversalCaptureRequest) -> Dict[str, Any]:
        """Process YouTube learning session"""
        metadata = request.metadata or {}
        
        return {
            'content_type': 'video_learning',
            'video_title': request.title,
            'channel': metadata.get('channel', 'Unknown'),
            'watched_duration': metadata.get('watched_minutes', 0),
            'total_duration': metadata.get('total_minutes', 0),
            'user_notes_timestamps': metadata.get('timestamped_notes', []),
            'key_segments': self._extract_learning_segments(metadata),
            'video_metadata': {
                'video_id': metadata.get('video_id'),
                'channel_id': metadata.get('channel_id'),
                'category': metadata.get('category', 'Education'),
                'language': metadata.get('language', 'en')
            },
            'thread_signals': self._extract_topic_keywords(request.content),
            'resume_context': {
                'resume_type': 'video',
                'video_id': metadata.get('video_id'),
                'last_timestamp': metadata.get('last_watched_timestamp', 0),
                'resume_url': self._build_youtube_resume_url(
                    metadata.get('video_id'), 
                    metadata.get('last_watched_timestamp', 0)
                )
            }
        }
    
    def _process_manual_note(self, request: UniversalCaptureRequest) -> Dict[str, Any]:
        """Process quick manual note"""
        metadata = request.metadata or {}
        
        return {
            'content_type': 'quick_note',
            'note_text': request.content,
            'note_context': metadata.get('context', 'general'),
            'user_intent': metadata.get('intent', 'thought'),
            'location_context': metadata.get('location'),
            'related_activity': metadata.get('related_activity'),
            'note_metadata': {
                'input_method': metadata.get('input_method', 'typing'),
                'note_length': len(request.content),
                'urgency': metadata.get('urgency', 'normal')
            },
            'thread_signals': self._extract_topic_keywords(request.content),
            'resume_context': {
                'resume_type': 'note',
                'context': metadata.get('context'),
                'related_url': request.source_url
            }
        }
    
    # Helper methods
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        if not url or url == 'unknown':
            return 'unknown'
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except:
            return 'unknown'
    
    def _extract_topic_keywords(self, content: str) -> List[str]:
        """Simple keyword extraction for thread detection"""
        # Simple implementation - could be enhanced with NLP
        keywords = []
        content_lower = content.lower()
        
        # Tech keywords
        tech_keywords = ['python', 'javascript', 'react', 'machine learning', 'ai', 'database', 'api', 'neural network']
        for keyword in tech_keywords:
            if keyword in content_lower:
                keywords.append(keyword)
        
        return keywords[:5]  # Limit to 5 keywords
    
    def _extract_user_questions(self, content: str) -> List[str]:
        """Extract user questions from AI conversation"""
        questions = []
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.endswith('?') and len(line) > 10:
                questions.append(line)
        return questions[:3]  # Top 3 questions
    
    def _extract_key_answers(self, content: str) -> List[str]:
        """Extract key answers from AI conversation"""
        # Simple implementation - look for sentences with key phrases
        answers = []
        sentences = content.split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if any(phrase in sentence.lower() for phrase in ['the key is', 'important to', 'you should']):
                answers.append(sentence + '.')
        return answers[:3]  # Top 3 answers
    
    def _extract_actionable_items(self, content: str) -> List[str]:
        """Extract actionable items"""
        actions = []
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if any(starter in line.lower() for starter in ['try', 'implement', 'use', 'create', 'build']):
                actions.append(line)
        return actions[:2]  # Top 2 actions
    
    def _get_last_user_question(self, content: str) -> str:
        """Get the last question user asked"""
        questions = self._extract_user_questions(content)
        return questions[-1] if questions else ""
    
    def _extract_learning_segments(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract key learning segments from video"""
        segments = []
        timestamped_notes = metadata.get('timestamped_notes', [])
        for note in timestamped_notes:
            segments.append({
                'timestamp': note.get('timestamp', 0),
                'description': note.get('note', ''),
                'importance': 'high' if 'important' in note.get('note', '').lower() else 'medium'
            })
        return segments
    
    def _build_youtube_resume_url(self, video_id: str, timestamp: int) -> str:
        """Build YouTube URL with timestamp"""
        if video_id and timestamp:
            return f"https://youtube.com/watch?v={video_id}&t={timestamp}s"
        return ""

# Initialize content processor
content_processor = ContentTypeProcessor()
# Utility functions

def serialize_for_json(obj):
    """Convert datetime objects and other non-serializable objects to JSON-safe formats"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(serialize_for_json(item) for item in obj)
    elif isinstance(obj, set):
        return list(serialize_for_json(item) for item in obj)
    elif hasattr(obj, '__dict__'):
        return serialize_for_json(obj.__dict__)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        try:
            return [serialize_for_json(item) for item in obj]
        except:
            return str(obj)
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)

def hash_content(content: str) -> str:
    """Create hash of content to detect duplicates"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def is_duplicate_content(note_content: str) -> bool:
    """Check if content is duplicate"""
    content_hash = hash_content(note_content)
    if content_hash in content_hashes:
        return True
    content_hashes.add(content_hash)
    return False

# Exception handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with detailed information"""
    logger.error(f"HTTP {exc.status_code} error: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "error_type": type(exc).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "debug": str(traceback.format_exc()) if app.debug else None
        }
    )

# API Endpoints

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Smart Notes FastAPI Server",
        "version": "2.0.0",
        "server_type": "FastAPI ASGI",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_status": "available" if pipeline_orchestrator else "unavailable",
        "documentation": {
            "interactive_docs": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json"
        },
        "endpoints": {
            "health": "/api/health",
            "status": "/api/status",
            "notes_batch": "/api/notes/batch",
            "bake": "/api/bake",
            "notes": "/api/notes",
            "batches": "/api/batches",
            "results": "/api/results"
        }
    }

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for extension connectivity"""
    try:
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            version="2.0.0",
            service="smart-notes-api",
            server_type="FastAPI ASGI",
            debug_mode=app.debug,
            endpoints={
                "health": "/api/health",
                "notes_batch": "/api/notes/batch",
                "bake": "/api/bake",
                "notes": "/api/notes",
                "batches": "/api/batches",
                "results": "/api/results",
                "docs": "/docs"
            }
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/api/status")
async def get_status():
    """Get detailed server status"""
    try:
        return {
            "server": "Smart Notes FastAPI API",
            "status": "running",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "debug_mode": app.debug,
            "python_version": sys.version,
            "fastapi_version": "2.0.0+",
            "stats": {
                "notes_in_memory": len(notes_storage),
                "batches_processed": len(batches_storage),
                "processing_results": len(processing_results)
            },
            "pipeline_orchestrator": {
                "available": pipeline_orchestrator is not None,
                "status": "operational" if pipeline_orchestrator else "unavailable"
            }
        }
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notes/batch", response_model=BatchResponse)
async def receive_batch(batch_request: BatchRequest, background_tasks: BackgroundTasks):
    """Receive a batch of notes from the extension"""
    try:
        logger.info("=== BATCH PROCESSING REQUEST ===")
        
        batch_id = batch_request.batch_id or str(uuid.uuid4())
        notes = batch_request.notes
        
        # Check for duplicate batch
        if batch_id in processed_batches:
            logger.warning(f"Duplicate batch detected: {batch_id}")
            return BatchResponse(
                success=True,
                status="duplicate",
                batch_id=batch_id,
                notes_received=len(notes),
                notes_processed=0,
                duplicates_filtered=0,
                message="Batch already processed",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        logger.info(f"Processing batch {batch_id} with {len(notes)} notes")
        
        # Filter duplicates
        unique_notes = []
        duplicate_count = 0
        
        for note in notes:
            note_content = note.content
            if note_content and not is_duplicate_content(note_content):
                # Convert Pydantic model to dict for processing
                note_dict = {
                    "content": note.content,
                    "user_id": note.user_id,
                    "source_url": note.source_url,
                    "title": note.title,
                    "timestamp": note.timestamp,
                    "intent": note.intent,
                    "user_note": note.user_note
                }
                
                # Handle legacy fields
                if note.source:
                    note_dict["source"] = {
                        "url": note.source.url,
                        "title": note.source.title,
                        "domain": note.source.domain
                    }
                
                if note.metadata:
                    note_dict["metadata"] = {
                        "content_category": note.metadata.content_category,
                        "captured_at": note.metadata.captured_at,
                        "tags": note.metadata.tags,
                        "local_id": note.metadata.local_id
                    }
                
                unique_notes.append(note_dict)
            else:
                duplicate_count += 1
                logger.info(f"Skipping duplicate note: {note_content[:50]}...")
        
        logger.info(f"Filtered {duplicate_count} duplicates, processing {len(unique_notes)} unique notes")
        
        # Mark batch as processed
        processed_batches.add(batch_id)
        
        # Store batch metadata
        batch_info = {
            "batch_id": batch_id,
            "timestamp": batch_request.timestamp or datetime.now(timezone.utc).isoformat(),
            "batch_size": len(notes),
            "unique_notes": len(unique_notes),
            "duplicates_filtered": duplicate_count,
            "status": "received",
            "notes_count": len(unique_notes),
            "processing_mode": batch_request.processing_mode
        }
        
        # Save and process if we have unique notes
        if unique_notes:
            # Save to file
            batch_file = BATCHES_DIR / f"{batch_id}.json"
            with open(batch_file, 'w') as f:
                json.dump({
                    "batch_info": batch_info,
                    "notes": unique_notes
                }, f, indent=2)
            
            # Add timestamps and store in memory
            timestamped_notes = []
            for note in unique_notes:
                note['stored_at'] = datetime.now(timezone.utc).isoformat()
                timestamped_notes.append(note)
            
            notes_storage.extend(timestamped_notes)
            
            # Process in background
            background_tasks.add_task(save_individual_notes_background, unique_notes, batch_id)
            background_tasks.add_task(process_batch_background, batch_id, unique_notes)
        
        batches_storage.append(batch_info)
        
        logger.info(f"Batch {batch_id} queued for processing")
        
        return BatchResponse(
            success=True,
            status="success",
            batch_id=batch_id,
            notes_received=len(notes),
            notes_processed=len(unique_notes),
            duplicates_filtered=duplicate_count,
            message=f"Batch received: {len(unique_notes)} unique notes, {duplicate_count} duplicates filtered",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.post("/api/bake", response_model=BakeResponse)
async def trigger_bake(bake_request: BakeRequest, background_tasks: BackgroundTasks):
    """Trigger the AI processing pipeline (bake) on collected notes"""
    global last_bake_time
    
    try:
        logger.info("=== BAKE REQUEST ===")
        
        current_time = datetime.now(timezone.utc)
        
        # Throttle check
        if last_bake_time is not None:
            time_diff = (current_time - last_bake_time).total_seconds()
            if time_diff < BAKE_THROTTLE_SECONDS:
                wait_time = BAKE_THROTTLE_SECONDS - time_diff
                logger.warning(f"Bake throttled. {wait_time:.1f} seconds remaining.")
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {wait_time:.1f} seconds before starting another bake."
                )
        
        bake_id = bake_request.bake_id or str(uuid.uuid4())
        
        # Check for duplicate bake
        if bake_id in processed_bakes:
            logger.warning(f"Duplicate bake detected: {bake_id}")
            return BakeResponse(
                success=True,
                status="duplicate",
                bake_id=bake_id,
                message="Bake already processed",
                notes_count=len(notes_storage),
                timestamp=current_time.isoformat()
            )
        
        # Mark bake as processed
        processed_bakes.add(bake_id)
        last_bake_time = current_time
        
        # Prepare bake data
        bake_data = {
            "bake_id": bake_id,
            "timestamp": bake_request.timestamp or datetime.now(timezone.utc).isoformat(),
            "source": bake_request.source or bake_request.trigger_source,
            "include_additional_notes": bake_request.includeAdditionalNotes,
            "additional_notes": bake_request.additionalNotes,
            "total_notes": len(notes_storage),
            "status": "initiated"
        }
        
        # Save bake request
        bake_file = RESULTS_DIR / f"bake_{bake_id}.json"
        with open(bake_file, 'w') as f:
            json.dump(bake_data, f, indent=2)
        
        # Process in background
        background_tasks.add_task(process_bake_background, bake_data)
        
        logger.info(f"Bake {bake_id} initiated with {len(notes_storage)} notes")
        
        return BakeResponse(
            success=True,
            status="success",
            bake_id=bake_id,
            message="Bake process initiated",
            notes_count=len(notes_storage),
            timestamp=datetime.now(timezone.utc).isoformat(),
            data={
                "bake_id": bake_id,
                "notes_count": len(notes_storage)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating bake: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error initiating bake: {str(e)}"
        )

@app.get("/api/notes", response_model=NotesResponse)
async def get_notes(
    limit: int = Query(50, ge=1, le=1000, description="Number of notes to return"),
    offset: int = Query(0, ge=0, description="Number of notes to skip")
):
    """Get stored notes from memory (for popup display)"""
    try:
        total = len(notes_storage)
        notes = notes_storage[offset:offset + limit]
        
        display_notes = []
        for i, note in enumerate(notes):
            display_note = {
                "id": note.get('id') or note.get('metadata', {}).get('local_id') or f"note_{offset + i}",
                "title": note.get('source', {}).get('title', note.get('title', 'Untitled')),
                "url": note.get('source', {}).get('url', note.get('source_url', '')),
                "content_preview": note.get('content', '')[:200] + ('...' if len(note.get('content', '')) > 200 else ''),
                "content_full": note.get('content', ''),
                "captured_at": note.get('metadata', {}).get('captured_at', note.get('timestamp', 'unknown')),
                "stored_at": note.get('stored_at', 'unknown'),
                "category": note.get('metadata', {}).get('content_category', 'general'),
                "tags": note.get('metadata', {}).get('tags', []),
                "word_count": len(note.get('content', '').split()),
                "intent": note.get('intent', 'learn'),
                "user_note": note.get('user_note', ''),
                "raw_note": note
            }
            display_notes.append(display_note)
        
        return NotesResponse(
            notes=display_notes,
            pagination=PaginationInfo(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + limit) < total
            ),
            stats={
                "total_notes": total,
                "returned": len(display_notes),
                "memory_usage": "display_optimized"
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Error retrieving notes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving notes: {str(e)}")

@app.get("/api/batches")
async def get_batches():
    """Get batch processing history"""
    try:
        return {
            "batches": batches_storage,
            "total_batches": len(batches_storage),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving batches: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving batches: {str(e)}")

@app.get("/api/results")
async def get_results(
    bake_id: Optional[str] = Query(None, description="Specific bake ID to retrieve")
):
    """Get processing results"""
    try:
        if bake_id:
            # Look for specific bake result
            for result in processing_results:
                if result.get('bake_id') == bake_id:
                    formatted_result = {
                        'bake_id': bake_id,
                        'status': result.get('status', 'unknown'),
                        'found': True,
                        'source': 'memory',
                        
                        'key_metrics': {
                            'captures_processed': result.get('processing_summary', {}).get('captures_processed', 0),
                            'concepts_extracted': result.get('processing_summary', {}).get('concepts_extracted', 0),
                            'api_calls_saved': result.get('batch_optimization', {}).get('api_calls_saved', 0),
                            'processing_time_seconds': result.get('processing_summary', {}).get('processing_time_seconds', 0),
                            'session_theme': result.get('processing_summary', {}).get('session_theme', 'general')
                        },
                        
                        'result': result,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    return formatted_result
            
            raise HTTPException(
                status_code=404,
                detail=f"No results found for bake_id: {bake_id}"
            )
        
        else:
            total_captures = sum(r.get('processing_summary', {}).get('captures_processed', 0) for r in processing_results)
            total_api_calls_saved = sum(r.get('batch_optimization', {}).get('api_calls_saved', 0) for r in processing_results)
            
            return {
                "results": processing_results,
                "summary": {
                    "total_results": len(processing_results),
                    "total_captures_processed": total_captures,
                    "total_api_calls_saved": total_api_calls_saved,
                    "successful_bakes": len([r for r in processing_results if r.get('status') == 'completed'])
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

@app.delete("/api/notes")
async def clear_notes():
    """Clear all stored notes (for testing)"""
    try:
        global notes_storage
        notes_storage = []
        logger.info("All notes cleared")
        return {
            "status": "success", 
            "message": "All notes cleared",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing notes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing notes: {str(e)}")

@app.post("/api/cleanup")
async def cleanup_data():
    """Clean up old processed IDs and duplicate tracking"""
    global processed_batches, processed_bakes, content_hashes
    
    try:
        # Keep only recent IDs (last 1000 each)
        if len(processed_batches) > 1000:
            processed_batches = set(list(processed_batches)[-500:])
        
        if len(processed_bakes) > 1000:
            processed_bakes = set(list(processed_bakes)[-500:])
        
        if len(content_hashes) > 5000:
            content_hashes = set(list(content_hashes)[-2500:])
        
        logger.info("Cleanup completed")
        
        return {
            "success": True,
            "message": "Cleanup completed",
            "stats": {
                "processed_batches": len(processed_batches),
                "processed_bakes": len(processed_bakes),
                "content_hashes": len(content_hashes)
            }
        }
        
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notes/files")
async def get_notes_files_info():
    """Get information about stored note files (utility endpoint)"""
    try:
        note_files = list(NOTES_DIR.glob("note_*.json"))
        
        file_info = []
        for note_file in note_files:
            file_info.append({
                "filename": note_file.name,
                "size_bytes": note_file.stat().st_size,
                "created_at": datetime.fromtimestamp(note_file.stat().st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(note_file.stat().st_mtime).isoformat()
            })
        
        return {
            "file_count": len(file_info),
            "files": file_info,
            "total_size_bytes": sum(f["size_bytes"] for f in file_info),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting file info: {str(e)}")

# Background processing functions

async def process_batch_background(batch_id: str, notes: List[Dict[str, Any]]):
    """Background processing of a batch of notes"""
    logger.info(f"Processing batch {batch_id} in background")
    
    try:
        # Simulate processing time
        await asyncio.sleep(2)
        
        processed_notes = []
        for note in notes:
            processed_note = {
                "original": note,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processing_status": "completed",
                "insights": f"Processed note from {note.get('source', {}).get('url', note.get('source_url', 'unknown'))}",
                "categories": [note.get('metadata', {}).get('content_category', note.get('intent', 'general'))],
            }
            processed_notes.append(processed_note)
        
        # Update batch status
        batch_result = {
            "batch_id": batch_id,
            "status": "completed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "notes_processed": len(processed_notes),
            "results": processed_notes
        }
        
        # Save results
        result_file = BATCHES_DIR / f"{batch_id}_result.json"
        with open(result_file, 'w') as f:
            json.dump(batch_result, f, indent=2)
        
        logger.info(f"Batch {batch_id} processing completed")
        
    except Exception as e:
        logger.error(f"Error processing batch {batch_id}: {str(e)}")
        logger.error(traceback.format_exc())

async def process_bake_background(bake_data: Dict[str, Any]):
    """Background processing of bake request"""
    bake_id = bake_data['bake_id']
    
    print(f"\n🎬 === BACKGROUND THREAD EXECUTING for {bake_id} ===")
    print(f"📊 Notes in storage: {len(notes_storage)}")
    
    logger.info(f"Processing bake {bake_id} in background")
    
    try:
        if not pipeline_orchestrator:
            raise Exception("Pipeline orchestrator not available")
        
        session_notes = notes_storage.copy()
        print(f"📋 Running pipeline on {len(session_notes)} notes for bake {bake_id}")
        
        try:
            pipeline_results = pipeline_orchestrator.run_pipeline(session_notes, bake_data)
            print(f"✅ PIPELINE COMPLETED. Result keys: {list(pipeline_results.keys())}")
        except Exception as pipeline_error:
            logger.error(f"Pipeline execution failed for {bake_id}: {str(pipeline_error)}")
            raise pipeline_error
        
        try:
            api_response = {
                'bake_id': bake_id,
                'status': pipeline_results.get('status', 'completed'),
                'processed_at': pipeline_results.get('processed_at', datetime.now(timezone.utc).isoformat()),
                'input_notes_count': len(session_notes),
                
                'batch_optimization': pipeline_results.get('batch_optimization', {}),
                
                'processing_summary': {
                    'captures_processed': pipeline_results.get('summary', {}).get('captures_processed', len(session_notes)),
                    'concepts_extracted': pipeline_results.get('summary', {}).get('concepts_extracted', 0),
                    'api_calls_saved': pipeline_results.get('batch_optimization', {}).get('api_calls_saved', 0),
                    'processing_time_seconds': pipeline_results.get('processing_time', 0),
                    'session_theme': pipeline_results.get('learning_analysis', {}).get('session_theme', 'general')
                },
                
                'insights': pipeline_results.get('learning_analysis', {}),
                'knowledge_insights': pipeline_results.get('knowledge_insights', {}),
                'outputs': pipeline_results.get('outputs', {}),
                
                'detailed_results': pipeline_results,
                
                'pipeline_metadata': {
                    'pipeline_version': pipeline_results.get('metadata', {}).get('pipeline_version', '1.1.0'),
                    'nodes_executed': pipeline_results.get('metadata', {}).get('nodes_executed', 0),
                    'input_format': 'minimal_capture'
                }
            }
        except Exception as format_error:
            logger.error(f"Result formatting failed for {bake_id}: {str(format_error)}")
            api_response = {
                'bake_id': bake_id,
                'status': 'completed_with_formatting_issues',
                'processed_at': datetime.now(timezone.utc).isoformat(),
                'input_notes_count': len(session_notes),
                'batch_optimization': {},
                'processing_summary': {
                    'captures_processed': len(session_notes),
                    'concepts_extracted': 0,
                    'api_calls_saved': 0,
                    'processing_time_seconds': 0,
                    'session_theme': 'general'
                },
                'error': f'Formatting error: {str(format_error)}',
                'raw_pipeline_results': pipeline_results
            }
        
        processing_results.append(api_response)
        print(f"✅ FORMATTED RESULT ADDED TO MEMORY for bake {bake_id}")
        
        batch_metrics = api_response.get('batch_optimization', {})
        api_calls_saved = batch_metrics.get('api_calls_saved', 0)

        if api_calls_saved > 0:
            print(f"🎉 BATCH OPTIMIZATION SUCCESS: {api_calls_saved} API calls saved!")
            logger.info(f"Batch optimization successful: {api_calls_saved} API calls saved")
        else:
            print(f"⚠️  No batch optimization detected (this might be expected for small batches)")
            logger.info(f"No batch optimization detected for bake {bake_id}")

        try:
            result_file = RESULTS_DIR / f"bake_{bake_id}_pipeline_result.json"
            with open(result_file, 'w') as f:
                json.dump(api_response, f, indent=2, default=str)
            logger.info(f"Results saved to file: {result_file}")
        except Exception as save_error:
            logger.warning(f"Failed to save results to file: {str(save_error)}")
        
        logger.info(f"Pipeline bake {bake_id} completed successfully")
        print(f"✅ BACKGROUND PROCESSING COMPLETE for {bake_id}")
                
    except Exception as e:
        print(f"❌ ERROR in background processing for {bake_id}: {str(e)}")
        logger.error(f"Error processing bake {bake_id}: {str(e)}")
        logger.error(traceback.format_exc())
                
        error_result = {
            "bake_id": bake_id,
            "status": "failed",
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "input_notes_count": len(notes_storage) if notes_storage else 0,
            "error": str(e),
            "error_type": type(e).__name__,
            "error_context": {
                "pipeline_orchestrator_available": pipeline_orchestrator is not None,
                "notes_storage_count": len(notes_storage) if notes_storage else 0,
                "bake_data_keys": list(bake_data.keys()) if bake_data else []
            },
            "batch_optimization": {},
            "processing_summary": {
                "captures_processed": 0,
                "concepts_extracted": 0,
                "api_calls_saved": 0,
                "processing_time_seconds": 0,
                "session_theme": "error"
            }
        }

        processing_results.append(error_result)
        print(f"❌ ERROR RESULT ADDED TO MEMORY for bake {bake_id}")

        try:
            error_file = RESULTS_DIR / f"bake_{bake_id}_error.json"
            with open(error_file, 'w') as f:
                json.dump(error_result, f, indent=2, default=str)
        except Exception:
            pass

async def save_individual_notes_background(notes: List[Dict[str, Any]], batch_id: str):
    """Save individual notes to files in background (for persistence)"""
    try:
        logger.info(f"Background saving {len(notes)} notes to files")
        
        for i, note in enumerate(notes):
            note_id = note.get('id') or note.get('metadata', {}).get('local_id') or f"{batch_id}_note_{i}"
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            
            note_filename = f"note_{timestamp}_{note_id}.json"
            note_file = NOTES_DIR / note_filename
            
            note_data = {
                "note_id": note_id,
                "batch_id": batch_id,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "source": note.get('source', {}),
                "metadata": note.get('metadata', {}),
                "content": note.get('content', ''),
                "original_note": note
            }
            
            # Save individual note
            with open(note_file, 'w') as f:
                json.dump(note_data, f, indent=2)
            
        logger.info(f"Background file save completed for batch {batch_id}")
            
    except Exception as e:
        logger.error(f"Error in background file saving: {str(e)}")

# Application startup
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info("🚀 FastAPI Smart Notes API Server starting up...")
    logger.info("📊 Server will run on: http://localhost:8000")
    logger.info("🔧 Health check: http://localhost:8000/api/health")
    logger.info("📚 Interactive docs: http://localhost:8000/docs")
    logger.info("📖 ReDoc: http://localhost:8000/redoc")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Smart Notes FastAPI Server...")
    print("📊 Server will run on: http://localhost:8000")
    print("🔧 Health check: http://localhost:8000/api/health")
    print("📚 Interactive docs: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")
    print("📍 Available endpoints:")
    print("  - GET  /              (Root)")
    print("  - GET  /api/health    (Health check)")
    print("  - GET  /api/status    (Status)")
    print("  - POST /api/notes/batch (Process notes)")
    print("  - POST /api/bake      (Bake notes)")
    print("  - GET  /api/notes     (Get notes)")
    print("  - GET  /api/batches   (Get batches)")
    print("  - GET  /api/results   (Get results)")
    print("  - DELETE /api/notes   (Clear notes)")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(
        "api_server_fastapi:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info"
    )