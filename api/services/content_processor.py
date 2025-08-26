"""
Content type processor service
"""
import logging
from typing import Dict, List, Any
from ..models.capture import UniversalCaptureRequest, CaptureType


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


# Create global instance
content_processor = ContentTypeProcessor()