"""
Rate limiting service
"""
import time
import logging
from typing import Dict, Any, Tuple
from collections import defaultdict

# Rate limiting storage and configuration
rate_limit_storage = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # 1 minute window
RATE_LIMIT_MAX_REQUESTS = 30  # 30 requests per minute per user
RATE_LIMIT_CLEANUP_INTERVAL = 300  # Clean up old entries every 5 minutes
last_cleanup_time = time.time()


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = RATE_LIMIT_MAX_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.logger = logging.getLogger(__name__)
    
    def is_allowed(self, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed and return rate limit info
        
        Returns:
            (allowed: bool, info: dict)
        """
        current_time = time.time()
        
        # Clean up old entries periodically
        self._cleanup_old_entries(current_time)
        
        # Get user's request history
        user_requests = rate_limit_storage[user_id]
        
        # Remove requests outside the time window
        cutoff_time = current_time - self.window_seconds
        user_requests[:] = [req_time for req_time in user_requests if req_time > cutoff_time]
        
        # Check if under limit
        request_count = len(user_requests)
        allowed = request_count < self.max_requests
        
        if allowed:
            # Add current request time
            user_requests.append(current_time)
        
        # Calculate rate limit info
        window_start = current_time - self.window_seconds
        requests_in_window = len(user_requests)
        remaining = max(0, self.max_requests - requests_in_window)
        reset_time = min(user_requests) + self.window_seconds if user_requests else current_time + self.window_seconds
        
        rate_limit_info = {
            'allowed': allowed,
            'limit': self.max_requests,
            'remaining': remaining,
            'reset_time': reset_time,
            'window_seconds': self.window_seconds,
            'current_requests': requests_in_window
        }
        
        if not allowed:
            self.logger.warning(f"Rate limit exceeded for user {user_id}: {requests_in_window}/{self.max_requests} requests")
        
        return allowed, rate_limit_info
    
    def _cleanup_old_entries(self, current_time: float):
        """Clean up old rate limit entries"""
        global last_cleanup_time
        
        if current_time - last_cleanup_time > RATE_LIMIT_CLEANUP_INTERVAL:
            cutoff_time = current_time - self.window_seconds * 2  # Keep extra buffer
            
            # Clean up old entries for all users
            users_to_remove = []
            for user_id, requests in rate_limit_storage.items():
                requests[:] = [req_time for req_time in requests if req_time > cutoff_time]
                if not requests:
                    users_to_remove.append(user_id)
            
            # Remove users with no recent requests
            for user_id in users_to_remove:
                del rate_limit_storage[user_id]
            
            last_cleanup_time = current_time
            self.logger.info(f"Rate limit cleanup completed. Active users: {len(rate_limit_storage)}")


# Create global instance
rate_limiter = RateLimiter()