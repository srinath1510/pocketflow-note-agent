from sqlalchemy import (
    Column, String, Text, DateTime, Float, Integer, Boolean, JSON, 
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class ResearchThread(Base):
    """Research threads for organizing captures"""
    __tablename__ = 'research_threads'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(500), nullable=False)
    emoji = Column(String(10), default='📚')
    domain = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    progress_score = Column(Float, default=0.0)
    capture_count = Column(Integer, default=0)
    status = Column(String(50), default='active')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    topics = Column(JSON, default=list)
    thread_metadata = Column(JSON, default=dict)
    
    # Relationships
    captures = relationship("Capture", back_populates="thread", cascade="all, delete-orphan")
    reading_sessions = relationship("ReadingSession", back_populates="thread", cascade="all, delete-orphan")
    timeline_entries = relationship("TimelineEntry", back_populates="thread", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_research_threads_user_status', 'user_id', 'status'),
        Index('ix_research_threads_last_active', 'last_active'),
        CheckConstraint("status IN ('active', 'paused', 'completed', 'archived')", name='valid_status'),
        CheckConstraint("progress_score >= 0.0 AND progress_score <= 1.0", name='valid_progress'),
    )

class ReadingSession(Base):
    """Reading sessions for tracking research activity"""
    __tablename__ = 'reading_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('research_threads.id'), nullable=True)
    session_type = Column(String(100), default='focused')
    duration_minutes = Column(Integer, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    context_data = Column(JSON, default=dict)
    capture_count = Column(Integer, default=0)
    
    # Relationships
    thread = relationship("ResearchThread", back_populates="reading_sessions")
    captures = relationship("Capture", back_populates="reading_session")
    
    __table_args__ = (
        Index('ix_reading_sessions_user_thread', 'user_id', 'thread_id'),
        Index('ix_reading_sessions_time_range', 'start_time', 'end_time'),
        Index('ix_reading_sessions_active', 'is_active'),
    )

class Capture(Base):
    """Enhanced captures table with multi-modal support"""
    __tablename__ = 'captures'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('research_threads.id'), nullable=True)
    reading_session_id = Column(UUID(as_uuid=True), ForeignKey('reading_sessions.id'), nullable=True)
    
    # Core content
    content = Column(Text, nullable=False)
    title = Column(String(1000), default='Untitled')
    source_url = Column(Text, nullable=True)
    
    # Enhanced fields
    capture_type = Column(String(100), default='web_content')
    intent = Column(String(100), default='learn')
    user_note = Column(Text, default='')
    
    # Timestamps
    captured_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Processing
    processing_status = Column(String(100), default='pending')
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    content_metadata = Column(JSON, default=dict)
    processed_metadata = Column(JSON, default=dict)
    resume_context = Column(JSON, default=dict)
    
    # Quick access
    domain = Column(String(255), nullable=True, index=True)
    word_count = Column(Integer, default=0)
    content_hash = Column(String(64), nullable=True, index=True)
    
    # Relationships
    thread = relationship("ResearchThread", back_populates="captures")
    reading_session = relationship("ReadingSession", back_populates="captures")
    timeline_entries = relationship("TimelineEntry", back_populates="capture", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('content_hash', 'user_id', name='uq_captures_content_user'),
    )

class TimelineEntry(Base):
    """Timeline entries for research continuity"""
    __tablename__ = 'timeline_entries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey('research_threads.id'), nullable=False)
    capture_id = Column(UUID(as_uuid=True), ForeignKey('captures.id'), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), nullable=False)
    entry_type = Column(String(100), default='capture')
    resume_context = Column(JSON, default=dict)
    quick_actions = Column(JSON, default=list)
    session_context = Column(JSON, default=dict)
    
    # Relationships
    thread = relationship("ResearchThread", back_populates="timeline_entries")
    capture = relationship("Capture", back_populates="timeline_entries")
    
    __table_args__ = (
        Index('ix_timeline_entries_thread_time', 'thread_id', 'timestamp'),
        Index('ix_timeline_entries_user_time', 'user_id', 'timestamp'),
        Index('ix_timeline_entries_type', 'entry_type'),
    )

class UserPreferences(Base):
    """User preferences and settings"""
    __tablename__ = 'user_preferences'
    
    user_id = Column(String(255), primary_key=True)
    default_thread_emoji = Column(String(10), default='📚')
    session_gap_hours = Column(Integer, default=2)
    auto_thread_assignment = Column(Boolean, default=True)
    resume_reminders = Column(Boolean, default=True)
    timeline_items_per_page = Column(Integer, default=50)
    analytics_enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    settings = Column(JSON, default=dict)