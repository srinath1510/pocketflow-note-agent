from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta, timezone
from .models import ResearchThread, ReadingSession, Capture, TimelineEntry, UserPreferences

class ThreadRepository:
    """Repository for research thread operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_thread(self, thread_data: Dict[str, Any]) -> ResearchThread:
        """Create new research thread"""
        thread = ResearchThread(**thread_data)
        self.db.add(thread)
        self.db.flush()
        return thread
    
    def get_user_threads(self, user_id: str, status: Optional[str] = None) -> List[ResearchThread]:
        """Get threads for a user"""
        query = self.db.query(ResearchThread).filter(ResearchThread.user_id == user_id)
        if status:
            query = query.filter(ResearchThread.status == status)
        return query.order_by(desc(ResearchThread.last_active)).all()
    
    def get_thread_by_id(self, thread_id: str, user_id: str) -> Optional[ResearchThread]:
        """Get specific thread by ID and user"""
        return self.db.query(ResearchThread).filter(
            and_(ResearchThread.id == thread_id, ResearchThread.user_id == user_id)
        ).first()
    
    def update_thread_activity(self, thread_id: str, user_id: str, increment_captures: bool = False):
        """Update thread last activity and optionally increment capture count"""
        thread = self.get_thread_by_id(thread_id, user_id)
        if thread:
            thread.last_active = datetime.now(timezone.utc)
            if increment_captures:
                thread.capture_count += 1
                thread.progress_score = min(1.0, thread.capture_count * 0.05)  # Simple progress calc

class CaptureRepository:
    """Repository for capture operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_capture(self, capture_data: Dict[str, Any]) -> Capture:
        """Create new capture"""
        capture = Capture(**capture_data)
        self.db.add(capture)
        self.db.flush()
        return capture
    
    def get_thread_captures(self, user_id: str, thread_id: str, limit: int = 50) -> List[Capture]:
        """Get captures for a thread"""
        return self.db.query(Capture).filter(
            and_(Capture.user_id == user_id, Capture.thread_id == thread_id)
        ).order_by(desc(Capture.captured_at)).limit(limit).all()
    
    def get_capture_by_id(self, capture_id: str) -> Optional[Capture]:
        """Get capture by ID"""
        return self.db.query(Capture).filter(Capture.id == capture_id).first()
    
    def check_duplicate(self, content_hash: str, user_id: str) -> bool:
        """Check if capture is duplicate"""
        return self.db.query(Capture).filter(
            and_(Capture.content_hash == content_hash, Capture.user_id == user_id)
        ).first() is not None

class SessionRepository:
    """Repository for reading session operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(self, session_data: Dict[str, Any]) -> ReadingSession:
        """Create new reading session"""
        session = ReadingSession(**session_data)
        self.db.add(session)
        self.db.flush()
        return session
    
    def get_active_session(self, user_id: str, thread_id: Optional[str] = None) -> Optional[ReadingSession]:
        """Get active session for user/thread"""
        query = self.db.query(ReadingSession).filter(
            and_(ReadingSession.user_id == user_id, ReadingSession.is_active == True)
        )
        if thread_id:
            query = query.filter(ReadingSession.thread_id == thread_id)
        return query.order_by(desc(ReadingSession.start_time)).first()
    
    def detect_session_boundaries(self, user_id: str, thread_id: str, gap_hours: int = 2) -> List[ReadingSession]:
        """Detect session boundaries based on time gaps"""
        captures = self.db.query(Capture).filter(
            and_(Capture.user_id == user_id, Capture.thread_id == thread_id)
        ).order_by(Capture.captured_at).all()
        
        sessions = []
        current_session_captures = []
        
        for capture in captures:
            if not current_session_captures:
                current_session_captures.append(capture)
                continue
            
            last_capture = current_session_captures[-1]
            time_gap = (capture.captured_at - last_capture.captured_at).total_seconds() / 3600
            
            if time_gap > gap_hours:
                # End current session
                session_data = self._create_session_from_captures(current_session_captures, user_id, thread_id)
                if session_data:
                    sessions.append(session_data)
                current_session_captures = [capture]
            else:
                current_session_captures.append(capture)
        
        # Add final session
        if current_session_captures:
            session_data = self._create_session_from_captures(current_session_captures, user_id, thread_id)
            if session_data:
                sessions.append(session_data)
        
        return sessions
    
    def _create_session_from_captures(self, captures: List[Capture], user_id: str, thread_id: str) -> Optional[Dict[str, Any]]:
        """Create session data from capture list"""
        if not captures:
            return None
        
        start_time = min(capture.captured_at for capture in captures)
        end_time = max(capture.captured_at for capture in captures)
        duration_minutes = int((end_time - start_time).total_seconds() / 60)
        
        return {
            'user_id': user_id,
            'thread_id': thread_id,
            'start_time': start_time,
            'end_time': end_time,
            'duration_minutes': duration_minutes,
            'capture_count': len(captures),
            'is_active': (datetime.now(timezone.utc) - end_time).total_seconds() < 4 * 3600  # 4 hours
        }

class TimelineRepository:
    """Repository for timeline operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_timeline_entry(self, entry_data: Dict[str, Any]) -> TimelineEntry:
        """Create timeline entry"""
        entry = TimelineEntry(**entry_data)
        self.db.add(entry)
        self.db.flush()
        return entry
    
    def get_thread_timeline(self, user_id: str, thread_id: str, limit: int = 50) -> List[TimelineEntry]:
        """Get timeline entries for a thread"""
        return self.db.query(TimelineEntry).filter(
            and_(TimelineEntry.user_id == user_id, TimelineEntry.thread_id == thread_id)
        ).order_by(desc(TimelineEntry.timestamp)).limit(limit).all()
