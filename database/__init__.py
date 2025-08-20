from .models import Base, ResearchThread, ReadingSession, Capture, TimelineEntry, UserPreferences
from .manager import DatabaseManager, get_db
from .repositories import ThreadRepository, CaptureRepository, SessionRepository, TimelineRepository
from .health import check_database_health
from .setup import setup_database

__all__ = [
    # Models
    'Base', 
    'ResearchThread', 
    'ReadingSession', 
    'Capture', 
    'TimelineEntry', 
    'UserPreferences',
    
    # Database management
    'DatabaseManager', 
    'get_db', 
    'db_manager',
    
    # Repositories (data access layer)
    'ThreadRepository',
    'CaptureRepository', 
    'SessionRepository',
    'TimelineRepository',
    
    # Utilities
    'check_database_health',
    'setup_database'
]