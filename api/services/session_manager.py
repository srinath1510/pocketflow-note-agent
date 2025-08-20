import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import uuid
from ..models.session import (
    ContinuationContext, 
    ThreadTimeline, 
    ResumeContext, 
    SessionBoundary,
    TimelineEntryDetail,
)

from database.manager import get_db
from database.repositories import ThreadRepository, CaptureRepository, TimelineRepository

import logging
logger = logging.getLogger(__name__)

def debug_import():
    try:
        logger.info("Current working directory: " + str(__file__))
        logger.info("Attempting import...")
        from ..utils.storage import notes_storage, threads_storage
        logger.info(f"✅ Import successful! notes_storage length: {len(notes_storage)}")
        return notes_storage, threads_storage
    except ImportError as e:
        logger.error(f"❌ Import failed: {str(e)}")
        logger.error(f"Available modules: {list(sys.modules.keys())}")
        return [], {}

# Call at the top of your class
notes_storage, threads_storage = debug_import()

class SessionManager:
    """Manages session continuity and timeline"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session_boundaries = {}  # thread_id -> List[SessionBoundary]
        self.active_sessions = {}     # thread_id -> current_session_id


    def get_continuation_context(self, user_id: str, thread_id: str) -> ContinuationContext:
        """Get context for resuming research in a thread"""
        try:
            # Get thread captures            
            thread_captures = self._get_thread_captures(user_id, thread_id)
            
            if not thread_captures:
                return ContinuationContext(
                    thread_id=thread_id,
                    continuation_ready=False,
                    context_summary="No previous activity found",
                    suggested_actions=["Start capturing content in this thread"]
                )
            
            # Detect session boundaries
            sessions = self._detect_session_boundaries(thread_captures)
            last_session = sessions[-1] if sessions else None
            
            # Generate resume points
            resume_points = self._generate_resume_points(thread_captures[-5:])  # Last 5 captures
            
            # Create context summary
            thread_data = threads_storage.get(user_id, {}).get(thread_id, {})
            thread_name = thread_data.get('name', 'Research Thread')
            
            context_summary = self._build_context_summary(
                thread_name, len(thread_captures), last_session, resume_points
            )
            
            # Generate suggested actions
            suggested_actions = self._generate_continuation_actions(
                thread_captures, last_session, resume_points
            )
            
            return ContinuationContext(
                thread_id=thread_id,
                continuation_ready=True,
                last_session=last_session,
                resume_points=resume_points,
                suggested_actions=suggested_actions,
                context_summary=context_summary,
                next_steps=self._generate_next_steps(thread_captures, thread_data)
            )
            
        except Exception as e:
            self.logger.error(f"Error getting continuation context: {str(e)}")
            return ContinuationContext(
                thread_id=thread_id,
                continuation_ready=False,
                context_summary=f"Error loading context: {str(e)}",
                suggested_actions=["Try refreshing or contact support"]
            )
    
    def get_thread_timeline(self, user_id: str, thread_id: str, limit: int = 50) -> ThreadTimeline:
        """Get detailed timeline for a research thread from database"""
        try:
            db = next(get_db())
            thread_repo = ThreadRepository(db)
            timeline_repo = TimelineRepository(db)
            
            # Get thread data
            thread = thread_repo.get_thread_by_id(thread_id, user_id)
            if not thread:
                raise ValueError(f"Thread {thread_id} not found")
            
            # Get timeline entries from database
            timeline_entries_db = timeline_repo.get_thread_timeline(user_id, thread_id, limit)
            
            # Convert to response format
            timeline_entries = []
            for entry in timeline_entries_db:
                timeline_entry = TimelineEntryDetail(
                    capture_id=str(entry.capture_id),
                    thread_id=str(entry.thread_id),
                    timestamp=entry.timestamp.isoformat(),
                    capture_type=entry.capture.capture_type if entry.capture else 'unknown',
                    source_title=entry.capture.title if entry.capture else 'Unknown',
                    source_url=entry.capture.source_url if entry.capture else None,
                    content_preview=entry.capture.content[:200] + "..." if entry.capture and len(entry.capture.content) > 200 else entry.capture.content if entry.capture else "",
                    resume_context=self._build_resume_context_from_db(entry),
                    session_context=entry.session_context or {},
                    quick_actions=entry.quick_actions or [],
                    related_captures=[]
                )
                timeline_entries.append(timeline_entry)
            
            # Get session boundaries
            captures = self._get_thread_captures(user_id, thread_id)
            session_boundaries = self._detect_session_boundaries(captures)
            
            # Calculate progress
            progress_indicators = {
                'total_captures': len(captures),
                'progress_score': thread.progress_score,
                'activity_trend': 'active' if session_boundaries and session_boundaries[-1].is_active else 'inactive'
            }
            
            return ThreadTimeline(
                thread_id=thread_id,
                thread_name=thread.name,
                timeline_entries=timeline_entries,
                session_boundaries=session_boundaries,
                total_entries=len(timeline_entries),
                date_range={
                    'earliest': timeline_entries[-1].timestamp if timeline_entries else '',
                    'latest': timeline_entries[0].timestamp if timeline_entries else ''
                },
                progress_indicators=progress_indicators
            )
            
        except Exception as e:
            self.logger.error(f"Error getting thread timeline: {str(e)}")
            raise
    
    def get_capture_resume_context(self, capture_id: str) -> Optional[ResumeContext]:
        """Get resume context for a specific capture from database"""
        try:
            db = next(get_db())
            capture_repo = CaptureRepository(db)
            capture = capture_repo.get_capture_by_id(capture_id)
            
            if not capture:
                return None
            
            # Build resume context from database data
            resume_actions = self._build_resume_actions(
                capture.capture_type,
                capture.resume_context or {},
                capture
            )
            
            return ResumeContext(
                resume_type=capture.resume_context.get('resume_type', 'web') if capture.resume_context else 'web',
                source_url=capture.source_url,
                last_position=capture.resume_context or {},
                progress_percentage=capture.resume_context.get('reading_progress', 0) if capture.resume_context else 0,
                user_context=capture.user_note or '',
                resume_actions=resume_actions
            )
                
        except Exception as e:
            self.logger.error(f"Error getting capture resume context: {str(e)}")
            return None
    
    def _get_thread_captures(self, user_id: str, thread_id: str) -> List[Dict[str, Any]]:
        """Get all captures for a thread from database"""
        try:
            db = next(get_db())
            capture_repo = CaptureRepository(db)
            captures = capture_repo.get_thread_captures(user_id, thread_id)
        
            # Convert SQLAlchemy objects to dicts for compatibility
            return [
                {
                    'capture_id': str(capture.id),
                    'user_id': capture.user_id,
                    'thread_id': str(capture.thread_id) if capture.thread_id else None,
                    'content': capture.content,
                    'title': capture.title,
                    'source_url': capture.source_url,
                    'capture_type': capture.capture_type,
                    'timestamp': capture.captured_at.isoformat(),
                    'processed_metadata': capture.processed_meta or {},
                    'resume_context': capture.resume_context or {},
                    'user_note': capture.user_note or ''
                }
                for capture in captures
            ]
        except Exception as e:
            self.logger.error(f"Database error getting thread captures: {str(e)}")
            return []
    
    def _detect_session_boundaries(self, captures: List[Dict[str, Any]]) -> List[SessionBoundary]:
        """Use database session repository for boundary detection"""
        if not captures:
            return []
        
        try:
            # Get user_id and thread_id from first capture
            user_id = captures[0].get('user_id')
            thread_id = captures[0].get('thread_id')
            
            if not user_id or not thread_id:
                return []
            
            db = next(get_db())
            session_repo = SessionRepository(db)
            sessions_data = session_repo.detect_session_boundaries(user_id, thread_id)
            
            # Convert to SessionBoundary objects
            return [
                SessionBoundary(
                    session_id=str(uuid.uuid4()),
                    start_time=session['start_time'].isoformat(),
                    end_time=session['end_time'].isoformat() if session['end_time'] else None,
                    duration_minutes=session['duration_minutes'],
                    capture_count=session['capture_count'],
                    is_active=session['is_active']
                )
                for session in sessions_data
            ]
        except Exception as e:
            self.logger.error(f"Error detecting session boundaries: {str(e)}")
            return []
    
    def _create_session_boundary(self, captures: List[Dict[str, Any]]) -> SessionBoundary:
        """Create session boundary from captures"""
        if not captures:
            return None
        
        timestamps = [capture.get('timestamp', '') for capture in captures if capture.get('timestamp')]
        timestamps.sort()
        
        start_time = timestamps[0] if timestamps else datetime.now(timezone.utc).isoformat()
        end_time = timestamps[-1] if len(timestamps) > 1 else None
        
        # Calculate duration
        duration_minutes = None
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
            except:
                pass
        
        # Check if session is recent (active within last 4 hours)
        is_active = False
        if end_time or start_time:
            last_activity = end_time or start_time
            try:
                last_dt = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                time_since = datetime.now(timezone.utc) - last_dt
                is_active = time_since.total_seconds() < 4 * 3600  # 4 hours
            except:
                pass
        
        return SessionBoundary(
            session_id=str(uuid.uuid4()),
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            capture_count=len(captures),
            is_active=is_active
        )
    
    def _generate_resume_points(self, recent_captures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate resume points from recent captures"""
        resume_points = []
        
        for capture in recent_captures:
            processed_metadata = capture.get('processed_metadata', {})
            resume_context = processed_metadata.get('resume_context', {})
            
            if resume_context:
                resume_point = {
                    'capture_id': capture.get('capture_id'),
                    'title': capture.get('title', 'Untitled'),
                    'type': capture.get('capture_type', 'web_content'),
                    'resume_type': resume_context.get('resume_type', 'web'),
                    'resume_url': self._build_resume_url(resume_context),
                    'context': self._build_resume_description(capture, resume_context),
                    'timestamp': capture.get('timestamp', ''),
                    'quick_resume': True
                }
                resume_points.append(resume_point)
        
        return resume_points
    
    def _build_resume_url(self, resume_context: Dict[str, Any]) -> str:
        """Build resume URL based on context"""
        resume_type = resume_context.get('resume_type', 'web')
        
        if resume_type == 'video' and resume_context.get('resume_url'):
            return resume_context['resume_url']
        elif resume_type == 'pdf' and resume_context.get('document_url'):
            return resume_context['document_url']
        elif resume_type == 'ai_chat' and resume_context.get('conversation_url'):
            return resume_context['conversation_url']
        elif resume_context.get('url'):
            return resume_context['url']
        
        return ''
    
    def _build_resume_description(self, capture: Dict[str, Any], resume_context: Dict[str, Any]) -> str:
        """Build human-readable resume description"""
        resume_type = resume_context.get('resume_type', 'web')
        title = capture.get('title', 'Untitled')
        
        if resume_type == 'video':
            timestamp = resume_context.get('last_timestamp', 0)
            minutes = timestamp // 60
            seconds = timestamp % 60
            return f"Resume '{title}' at {minutes}:{seconds:02d}"
        elif resume_type == 'pdf':
            page = resume_context.get('last_page', 1)
            progress = resume_context.get('reading_progress', 0)
            return f"Continue reading '{title}' from page {page} ({progress:.0%} complete)"
        elif resume_type == 'ai_chat':
            return f"Continue conversation about '{title}'"
        else:
            progress = resume_context.get('scroll_position', 0)
            if progress > 0:
                return f"Continue reading '{title}' ({progress:.0%} through)"
            else:
                return f"Read '{title}'"
    
    def _build_context_summary(self, thread_name: str, capture_count: int, 
                              last_session: Optional[SessionBoundary], 
                              resume_points: List[Dict[str, Any]]) -> str:
        """Build context summary for continuation"""
        parts = [f"Research thread '{thread_name}' has {capture_count} captures"]
        
        if last_session:
            if last_session.is_active:
                parts.append("with an active session in progress")
            else:
                duration = last_session.duration_minutes or 0
                parts.append(f"Last session: {duration} minutes with {last_session.capture_count} captures")
        
        if resume_points:
            parts.append(f"{len(resume_points)} items ready for continuation")
        
        return ". ".join(parts) + "."
    
    def _generate_continuation_actions(self, captures: List[Dict[str, Any]], 
                                     last_session: Optional[SessionBoundary],
                                     resume_points: List[Dict[str, Any]]) -> List[str]:
        """Generate suggested continuation actions"""
        actions = []
        
        if resume_points:
            # Prioritize video and PDF resumes
            video_resumes = [rp for rp in resume_points if rp['type'] == 'youtube_video']
            pdf_resumes = [rp for rp in resume_points if rp['type'] == 'pdf_reading']
            
            if video_resumes:
                actions.append(f"Resume watching: {video_resumes[0]['title']}")
            if pdf_resumes:
                actions.append(f"Continue reading: {pdf_resumes[0]['title']}")
            
            # Add general resume action
            if len(resume_points) > 2:
                actions.append(f"Review {len(resume_points)} resume points")
        
        # Add capture-based suggestions
        if captures:
            recent_types = [c.get('capture_type', 'web_content') for c in captures[-3:]]
            if 'ai_chat' in recent_types:
                actions.append("Ask follow-up questions on recent topics")
            if 'web_content' in recent_types:
                actions.append("Find related articles to continue research")
        
        # Default actions
        if not actions:
            actions = [
                "Add new content to this research thread",
                "Review previous captures for insights",
                "Switch to a different research thread"
            ]
        
        return actions[:4]  # Limit to 4 actions
    
    def _generate_next_steps(self, captures: List[Dict[str, Any]], 
                           thread_data: Dict[str, Any]) -> List[str]:
        """Generate next steps for research continuation"""
        next_steps = []
        
        # Analyze thread progress
        progress_score = thread_data.get('progress_score', 0)
        
        if progress_score < 0.3:
            next_steps.extend([
                "Gather more foundational content",
                "Search for beginner-friendly resources"
            ])
        elif progress_score < 0.7:
            next_steps.extend([
                "Dive deeper into specific concepts",
                "Look for practical examples and tutorials"
            ])
        else:
            next_steps.extend([
                "Explore advanced topics",
                "Find real-world applications and case studies"
            ])
        
        # Add content-type specific suggestions
        if captures:
            last_capture_type = captures[-1].get('capture_type', 'web_content')
            if last_capture_type == 'ai_chat':
                next_steps.append("Practice implementing the discussed concepts")
            elif last_capture_type == 'youtube_video':
                next_steps.append("Find complementary reading materials")
            elif last_capture_type == 'pdf_reading':
                next_steps.append("Search for video explanations of key concepts")
        
        return next_steps[:3]
    
    def _create_timeline_entry(self, capture: Dict[str, Any], thread_id: str) -> TimelineEntryDetail:
        """Create detailed timeline entry from capture"""
        processed_metadata = capture.get('processed_metadata', {})
        resume_context_data = processed_metadata.get('resume_context', {})
        
        # Build resume context
        resume_context = None
        if resume_context_data:
            resume_actions = self._build_resume_actions(
                capture.get('capture_type', 'web_content'),
                resume_context_data,
                capture
            )
            
            resume_context = ResumeContext(
                resume_type=resume_context_data.get('resume_type', 'web'),
                source_url=capture.get('source_url'),
                last_position=resume_context_data,
                progress_percentage=resume_context_data.get('reading_progress', 0),
                user_context=capture.get('user_note', ''),
                resume_actions=resume_actions
            )
        
        # Quick actions based on capture type
        capture_type = capture.get('capture_type', 'web_content')
        quick_actions = self._build_timeline_quick_actions(capture_type, capture)
        
        return TimelineEntryDetail(
            capture_id=capture.get('capture_id', ''),
            thread_id=thread_id,
            timestamp=capture.get('timestamp', ''),
            capture_type=capture_type,
            source_title=capture.get('title', 'Untitled'),
            source_url=capture.get('source_url'),
            content_preview=capture.get('content', '')[:200] + "..." if len(capture.get('content', '')) > 200 else capture.get('content', ''),
            resume_context=resume_context,
            session_context={'user_note': capture.get('user_note', '')},
            quick_actions=quick_actions,
            related_captures=[]  # Could be enhanced with similarity search
        )
    
    def _build_resume_actions(self, capture_type: str, resume_context: Dict[str, Any], 
                            capture: Dict[str, Any]) -> List[str]:
        """Build resume actions based on capture type"""
        actions = []
        
        if capture_type == 'youtube_video':
            actions = ["Resume video", "View transcript", "Take notes"]
        elif capture_type == 'pdf_reading':
            actions = ["Continue reading", "Jump to bookmarks", "Search document"]
        elif capture_type == 'ai_chat':
            actions = ["Continue conversation", "Ask follow-up", "Start new chat"]
        elif capture_type == 'web_content':
            actions = ["Continue reading", "Find related articles", "Take notes"]
        else:
            actions = ["Review content", "Take notes", "Find related"]
        
        return actions
    
    def _build_timeline_quick_actions(self, capture_type: str, capture: Dict[str, Any]) -> List[str]:
        """Build quick actions for timeline entries"""
        base_actions = ["View details", "Add to notes"]
        
        if capture.get('source_url'):
            base_actions.insert(0, "Open source")
        
        if capture_type == 'youtube_video':
            base_actions.append("Resume video")
        elif capture_type == 'pdf_reading':
            base_actions.append("Continue reading")
        elif capture_type == 'ai_chat':
            base_actions.append("Continue chat")
        
        return base_actions[:4]
    
    def _calculate_time_gap(self, timestamp1: str, timestamp2: str) -> float:
        """Calculate time gap in seconds between timestamps"""
        try:
            dt1 = datetime.fromisoformat(timestamp1.replace('Z', '+00:00'))
            dt2 = datetime.fromisoformat(timestamp2.replace('Z', '+00:00'))
            return abs((dt2 - dt1).total_seconds())
        except:
            return 0
    
    def _calculate_progress_indicators(self, captures: List[Dict[str, Any]], 
                                     thread_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate progress indicators for the thread"""
        if not captures:
            return {'total_captures': 0, 'progress_score': 0, 'activity_trend': 'inactive'}
        
        # Basic metrics
        total_captures = len(captures)
        progress_score = thread_data.get('progress_score', 0)
        
        # Activity trend (based on recent captures)
        recent_captures = [c for c in captures if self._is_recent(c.get('timestamp', ''), days=7)]
        
        if len(recent_captures) >= 3:
            activity_trend = 'very_active'
        elif len(recent_captures) >= 1:
            activity_trend = 'active'
        else:
            activity_trend = 'inactive'
        
        # Content type distribution
        content_types = {}
        for capture in captures:
            ctype = capture.get('capture_type', 'web_content')
            content_types[ctype] = content_types.get(ctype, 0) + 1
        
        return {
            'total_captures': total_captures,
            'progress_score': progress_score,
            'activity_trend': activity_trend,
            'content_type_distribution': content_types,
            'recent_activity_count': len(recent_captures)
        }
    
    def _is_recent(self, timestamp: str, days: int = 7) -> bool:
        """Check if timestamp is within recent days"""
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return (datetime.now(timezone.utc) - dt).days <= days
        except:
            return False

    def _calculate_resume_priority(self, resume_point: Dict[str, Any]) -> float:
        """Calculate priority score for resume points (0-1, higher = more important)"""
        score = 0.0
        
        # Base score by content type (videos and PDFs get higher priority)
        content_type = resume_point.get('type', 'web_content')
        type_scores = {
            'youtube_video': 0.4,
            'pdf_reading': 0.35,
            'ai_chat': 0.3,
            'web_content': 0.2,
            'quick_note': 0.1
        }
        score += type_scores.get(content_type, 0.2)
        
        # Recency boost (more recent = higher priority)
        timestamp = resume_point.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                
                if hours_ago < 2:      # Very recent
                    score += 0.3
                elif hours_ago < 24:   # Same day
                    score += 0.2
                elif hours_ago < 72:   # Last 3 days
                    score += 0.1
            except:
                pass
        
        # Progress-based boost (partially complete content gets priority)
        resume_type = resume_point.get('resume_type', 'web')
        if resume_type == 'video':
            # Video with progress gets boost
            score += 0.2
        elif resume_type == 'pdf':
            # PDF in progress gets boost
            score += 0.15
        
        # Title-based keywords (learning-related content)
        title = resume_point.get('title', '').lower()
        learning_keywords = ['tutorial', 'guide', 'learn', 'course', 'lesson', 'training']
        if any(keyword in title for keyword in learning_keywords):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()
    
    def get_thread_activity_summary(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Get activity summary for a thread (useful for analytics)"""
        try:
            captures = self._get_thread_captures(user_id, thread_id)
            
            if not captures:
                return {
                    'thread_id': thread_id,
                    'total_captures': 0,
                    'activity_summary': 'No activity'
                }
            
            # Time-based analysis
            timestamps = [c.get('timestamp', '') for c in captures if c.get('timestamp')]
            timestamps.sort()
            
            # Content type distribution
            content_types = {}
            for capture in captures:
                ctype = capture.get('capture_type', 'web_content')
                content_types[ctype] = content_types.get(ctype, 0) + 1
            
            # Session analysis
            sessions = self._detect_session_boundaries(captures)
            active_sessions = [s for s in sessions if s.is_active]
            
            # Recent activity (last 7 days)
            recent_captures = [c for c in captures if self._is_recent(c.get('timestamp', ''), days=7)]
            
            return {
                'thread_id': thread_id,
                'total_captures': len(captures),
                'content_type_distribution': content_types,
                'session_count': len(sessions),
                'active_sessions': len(active_sessions),
                'recent_activity_count': len(recent_captures),
                'date_range': {
                    'first_capture': timestamps[0] if timestamps else None,
                    'last_capture': timestamps[-1] if timestamps else None
                },
                'average_session_length': self._calculate_average_session_length(sessions)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting activity summary: {str(e)}")
            return {
                'thread_id': thread_id,
                'error': str(e)
            }
    
    def _calculate_average_session_length(self, sessions: List[SessionBoundary]) -> Optional[float]:
        """Calculate average session length in minutes"""
        durations = [s.duration_minutes for s in sessions if s.duration_minutes]
        return sum(durations) / len(durations) if durations else None
    
    def detect_session_patterns(self, user_id: str, thread_id: str) -> Dict[str, Any]:
        """Detect research patterns for the user (advanced analytics)"""
        try:
            captures = self._get_thread_captures(user_id, thread_id)
            sessions = self._detect_session_boundaries(captures)
            
            # Analyze session patterns
            patterns = {
                'thread_id': thread_id,
                'pattern_analysis': {}
            }
            
            if not sessions:
                patterns['pattern_analysis']['status'] = 'insufficient_data'
                return patterns
            
            # Time patterns
            session_times = []
            for session in sessions:
                if session.start_time:
                    try:
                        dt = datetime.fromisoformat(session.start_time.replace('Z', '+00:00'))
                        session_times.append(dt.hour)
                    except:
                        continue
            
            if session_times:
                patterns['pattern_analysis']['preferred_hours'] = {
                    'morning': len([h for h in session_times if 6 <= h < 12]),
                    'afternoon': len([h for h in session_times if 12 <= h < 18]),
                    'evening': len([h for h in session_times if 18 <= h < 24]),
                    'night': len([h for h in session_times if 0 <= h < 6])
                }
            
            # Session length patterns
            durations = [s.duration_minutes for s in sessions if s.duration_minutes]
            if durations:
                avg_duration = sum(durations) / len(durations)
                patterns['pattern_analysis']['session_behavior'] = {
                    'average_duration_minutes': round(avg_duration, 1),
                    'short_sessions': len([d for d in durations if d < 15]),
                    'medium_sessions': len([d for d in durations if 15 <= d < 60]),
                    'long_sessions': len([d for d in durations if d >= 60])
                }
            
            # Content type preferences
            content_preferences = {}
            for capture in captures:
                ctype = capture.get('capture_type', 'web_content')
                content_preferences[ctype] = content_preferences.get(ctype, 0) + 1
            
            if content_preferences:
                total_captures = sum(content_preferences.values())
                patterns['pattern_analysis']['content_preferences'] = {
                    ctype: {
                        'count': count,
                        'percentage': round((count / total_captures) * 100, 1)
                    }
                    for ctype, count in content_preferences.items()
                }
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Error detecting session patterns: {str(e)}")
            return {
                'thread_id': thread_id,
                'error': str(e)
            }
    
    def _get_thread_data(self, user_id: str, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get thread data from database"""
        try:
            db = next(get_db())
            thread_repo = ThreadRepository(db)
            thread = thread_repo.get_thread_by_id(thread_id, user_id)
            
            if thread:
                return {
                    'id': str(thread.id),
                    'name': thread.name,
                    'emoji': thread.emoji,
                    'domain': thread.domain,
                    'progress_score': thread.progress_score,
                    'capture_count': thread.capture_count,
                    'status': thread.status,
                    'created_at': thread.created_at.isoformat(),
                    'last_active': thread.last_active.isoformat(),
                    'topics': thread.topics or []
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting thread data: {str(e)}")
            return None
    
# Initialize session manager
session_manager = SessionManager()