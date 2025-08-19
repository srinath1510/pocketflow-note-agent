"""
Capture-related Pydantic models
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Any, Optional
from enum import Enum


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
    assignment_type: str = "suggested"  # "existing", "new", "suggested"
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