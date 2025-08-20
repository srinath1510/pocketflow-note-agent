import asyncio
import logging
from .manager import db_manager
from .models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Complete database setup"""
    try:
        logger.info("Starting database setup...")
        
        # Create all tables
        logger.info("Creating fresh tables...")
        Base.metadata.create_all(bind=db_manager.engine, checkfirst=True)
        
        logger.info("Database setup completed successfully")
        
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        raise


if __name__ == "__main__":
    setup_database()
