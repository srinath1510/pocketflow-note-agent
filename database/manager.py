from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
import logging

from models import Base

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.database_url = self._get_database_url()
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def _get_database_url(self) -> str:
        """Get database URL from environment or use default"""
        return os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:smartnotes123@localhost:5432/smartnotes'
        )
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def create_all_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine, checkfirst=True)
        self.logger.info("All tables created successfully")
    
    def drop_all_tables(self):
        """Drop all tables (use with caution)"""
        Base.metadata.drop_all(bind=self.engine)
        self.logger.warning("All tables dropped")

# Initialize database manager
db_manager = DatabaseManager()

def get_db() -> Session:
    """Dependency for FastAPI endpoints"""
    with db_manager.get_session() as session:
        yield session

# database/migrations.py - Database Migrations
from alembic import command
from alembic.config import Config
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def run_migrations():
    """Run database migrations"""
    try:
        # Create alembic config
        alembic_cfg_path = Path(__file__).parent / "alembic.ini"
        if not alembic_cfg_path.exists():
            create_alembic_config()
        
        alembic_cfg = Config(str(alembic_cfg_path))
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise

def create_alembic_config():
    """Create alembic configuration if it doesn't exist"""
    alembic_cfg_content = """
[alembic]
script_location = database/migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://postgres:smartnotes123@localhost:5432/smartnotes

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
    
    with open(Path(__file__).parent / "alembic.ini", 'w') as f:
        f.write(alembic_cfg_content)