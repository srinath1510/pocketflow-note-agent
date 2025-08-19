import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import uuid

class SessionManager:
    """Manages session continuity and timeline"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session_boundaries = {}  # thread_id -> List[SessionBoundary]
        self.active_sessions = {}     # thread_id -> current_session_id