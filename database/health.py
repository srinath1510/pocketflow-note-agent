from sqlalchemy import text
from .manager import db_manager
import logging

logger = logging.getLogger(__name__)

def check_database_health() -> dict:
    """Check database connectivity and performance"""
    health_status = {
        'status': 'healthy',
        'checks': {}
    }
    
    try:
        with db_manager.get_session() as session:
            # Test basic connectivity
            result = session.execute(text("SELECT 1")).scalar()
            health_status['checks']['connectivity'] = 'ok' if result == 1 else 'failed'
            
            # Check table existence
            tables = ['research_threads', 'captures', 'reading_sessions', 'timeline_entries']
            for table in tables:
                try:
                    count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    health_status['checks'][f'{table}_table'] = f'ok ({count} rows)'
                except Exception as e:
                    health_status['checks'][f'{table}_table'] = f'error: {str(e)}'
                    health_status['status'] = 'degraded'
            
            # Check indexes
            index_query = text("""
                SELECT schemaname, tablename, indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname LIKE 'ix_%'
            """)
            indexes = session.execute(index_query).fetchall()
            health_status['checks']['indexes'] = f'ok ({len(indexes)} indexes)'
            
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
        logger.error(f"Database health check failed: {str(e)}")
    
    return health_status