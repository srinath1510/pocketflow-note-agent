"""
Smart Notes API Package

A modular FastAPI application for AI-powered research continuity
and multi-modal content capture with intelligent thread management.
"""

__version__ = "2.0.0"
__title__ = "Smart Notes API"
__description__ = "AI-powered research continuity assistant"

# Expose main components for easier importing
from .main import app

# Services
from .services.thread_manager import thread_manager
from .services.content_processor import content_processor
from .services.rate_limiter import rate_limiter

# Storage
from .utils.storage import (
    notes_storage, 
    batches_storage, 
    threads_storage, 
    active_threads,
    processing_results
)

# Key models for external use
from .models.capture import UniversalCaptureRequest, UniversalCaptureResponse, CaptureType
from .models.thread import ResearchThread, ThreadCreateRequest, ThreadSwitchRequest
from .models.responses import HealthResponse, BatchResponse, BakeResponse

__all__ = [
    # Core app
    "app",
    
    # Services
    "thread_manager",
    "content_processor", 
    "rate_limiter",
    
    # Storage
    "notes_storage",
    "batches_storage",
    "threads_storage", 
    "active_threads",
    "processing_results",
    
    # Key models
    "UniversalCaptureRequest",
    "UniversalCaptureResponse", 
    "CaptureType",
    "ResearchThread",
    "ThreadCreateRequest",
    "ThreadSwitchRequest",
    "HealthResponse",
    "BatchResponse",
    "BakeResponse",
    
    # Package info
    "__version__",
    "__title__",
    "__description__"
]