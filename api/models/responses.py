"""
Response models for API endpoints
"""
from pydantic import BaseModel
from typing import Dict, List, Any, Optional


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