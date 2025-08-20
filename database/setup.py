import asyncio
import logging
from manager import db_manager
from models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Complete database setup"""
    try:
        logger.info("Starting database setup...")
        
        # Create all tables
        db_manager.create_all_tables()
        
        # Run any initial data setup
        setup_initial_data()
        
        logger.info("Database setup completed successfully")
        
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        raise

def setup_initial_data():
    """Setup initial data like default user preferences"""
    with db_manager.get_session() as session:
        # Add any initial data here
        pass

if __name__ == "__main__":
    setup_database()
