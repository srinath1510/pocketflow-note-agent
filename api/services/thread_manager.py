"""
Thread management service
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from ..models.thread import ResearchThread, ThreadCreateRequest, ThreadUpdateRequest, ThreadSwitchRequest
from ..utils.storage import threads_storage, active_threads, notes_storage


class ThreadManager:
    """Manages research threads and context switching"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_user_threads(self, user_id: str) -> List[ResearchThread]:
        """Get all threads for a user"""
        user_threads = threads_storage.get(user_id, {})
        return [ResearchThread(**thread) for thread in user_threads.values()]
    
    def get_active_thread(self, user_id: str) -> Optional[ResearchThread]:
        """Get user's active thread"""
        active_thread_id = active_threads.get(user_id)
        if active_thread_id and user_id in threads_storage:
            thread_data = threads_storage[user_id].get(active_thread_id)
            if thread_data:
                return ResearchThread(**thread_data)
        return None
    
    def create_thread(self, request: ThreadCreateRequest) -> ResearchThread:
        """Create new research thread"""
        thread_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        thread_data = {
            "id": thread_id,
            "user_id": request.user_id,
            "name": request.name,
            "emoji": request.emoji,
            "domain": request.domain,
            "progress_score": 0.0,
            "created_at": timestamp,
            "last_active": timestamp,
            "capture_count": 0,
            "topics": request.initial_topics,
            "status": "active"
        }
        
        # Initialize user threads storage if needed
        if request.user_id not in threads_storage:
            threads_storage[request.user_id] = {}
        
        threads_storage[request.user_id][thread_id] = thread_data
        
        # Set as active if user has no active thread
        if request.user_id not in active_threads:
            active_threads[request.user_id] = thread_id
        
        self.logger.info(f"Created thread {thread_id} for user {request.user_id}: {request.name}")
        return ResearchThread(**thread_data)
    
    def update_thread(self, user_id: str, thread_id: str, update: ThreadUpdateRequest) -> Optional[ResearchThread]:
        """Update existing thread"""
        if user_id not in threads_storage or thread_id not in threads_storage[user_id]:
            return None
        
        thread_data = threads_storage[user_id][thread_id]
        
        # Update fields if provided
        if update.name is not None:
            thread_data["name"] = update.name
        if update.emoji is not None:
            thread_data["emoji"] = update.emoji
        if update.domain is not None:
            thread_data["domain"] = update.domain
        if update.status is not None:
            thread_data["status"] = update.status
        if update.topics is not None:
            thread_data["topics"] = update.topics
        
        thread_data["last_active"] = datetime.now(timezone.utc).isoformat()
        
        self.logger.info(f"Updated thread {thread_id} for user {user_id}")
        return ResearchThread(**thread_data)
    
    def delete_thread(self, user_id: str, thread_id: str) -> bool:
        """Delete thread"""
        if user_id not in threads_storage or thread_id not in threads_storage[user_id]:
            return False
        
        del threads_storage[user_id][thread_id]
        
        # Clear active thread if it was deleted
        if active_threads.get(user_id) == thread_id:
            remaining_threads = list(threads_storage[user_id].keys())
            active_threads[user_id] = remaining_threads[0] if remaining_threads else None
        
        self.logger.info(f"Deleted thread {thread_id} for user {user_id}")
        return True
    
    def switch_context(self, request: ThreadSwitchRequest) -> Dict[str, Any]:
        """Switch user's active thread context"""
        from_thread = None
        if request.from_thread_id:
            from_thread_data = threads_storage.get(request.user_id, {}).get(request.from_thread_id)
            if from_thread_data:
                from_thread = ResearchThread(**from_thread_data)
        
        # Get target thread
        to_thread_data = threads_storage.get(request.user_id, {}).get(request.to_thread_id)
        if not to_thread_data:
            raise ValueError(f"Thread {request.to_thread_id} not found")
        
        to_thread = ResearchThread(**to_thread_data)
        
        # Update active thread
        active_threads[request.user_id] = request.to_thread_id
        
        # Update last_active timestamp
        to_thread_data["last_active"] = datetime.now(timezone.utc).isoformat()
        
        # Create context summary
        context_summary = {
            "previous_captures": self._get_recent_captures(request.user_id, request.from_thread_id) if request.from_thread_id else [],
            "target_thread_captures": self._get_recent_captures(request.user_id, request.to_thread_id),
            "suggested_actions": self._generate_context_switch_actions(from_thread, to_thread)
        }
        
        self.logger.info(f"Switched context for user {request.user_id}: {request.from_thread_id} -> {request.to_thread_id}")
        
        return {
            "from_thread": from_thread,
            "to_thread": to_thread,
            "context_summary": context_summary
        }
    
    def update_thread_activity(self, user_id: str, thread_id: str, capture_added: bool = False):
        """Update thread activity when captures are added"""
        if user_id in threads_storage and thread_id in threads_storage[user_id]:
            thread_data = threads_storage[user_id][thread_id]
            thread_data["last_active"] = datetime.now(timezone.utc).isoformat()
            
            if capture_added:
                thread_data["capture_count"] = thread_data.get("capture_count", 0) + 1
                # Simple progress calculation
                thread_data["progress_score"] = min(1.0, thread_data["capture_count"] * 0.1)
    
    def _get_recent_captures(self, user_id: str, thread_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent captures for a thread"""
        if not thread_id:
            return []
        
        # Filter captures by thread_id and user_id
        thread_captures = [
            capture for capture in notes_storage 
            if capture.get("user_id") == user_id and 
               capture.get("thread_id") == thread_id
        ]
        
        # Sort by timestamp and return recent ones
        thread_captures.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return thread_captures[:limit]
    
    def _generate_context_switch_actions(self, from_thread: Optional[ResearchThread], to_thread: ResearchThread) -> List[str]:
        """Generate suggested actions for context switch"""
        actions = []
        
        if from_thread:
            actions.append(f"Save progress in '{from_thread.name}' thread")
        
        actions.extend([
            f"Review recent activity in '{to_thread.name}'",
            f"Continue research on: {', '.join(to_thread.topics[:3]) if to_thread.topics else 'general topics'}",
            "Add new captures to this thread"
        ])
        
        return actions


# Create global instance
thread_manager = ThreadManager()