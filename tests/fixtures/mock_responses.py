"""
Advanced mock responses and patterns extracted from legacy tests.
"""

from unittest.mock import Mock, MagicMock
from datetime import datetime
import json


def create_advanced_notion_mock():
    """Create sophisticated Notion API mock with realistic responses."""
    
    # Mock health check response
    mock_get = Mock()
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {'object': 'user', 'id': 'test_user_123'}
    
    # Mock database creation response
    mock_database_response = Mock()
    mock_database_response.status_code = 200
    mock_database_response.json.return_value = {
        'id': 'test_db_123',
        'object': 'database',
        'title': [{'plain_text': 'BrowserBud - Test Database'}],
        'properties': {
            'Name': {'title': {}},
            'Status': {'select': {'options': []}},
            'Tags': {'multi_select': {'options': []}}
        },
        'url': 'https://notion.so/test_db_123'
    }
    
    # Mock page creation response
    mock_page_response = Mock()
    mock_page_response.status_code = 201
    mock_page_response.json.return_value = {
        'id': 'test_page_456',
        'object': 'page',
        'url': 'https://notion.so/test_page_456',
        'properties': {
            'title': {
                'title': [{'plain_text': 'Test Page Title'}]
            }
        },
        'parent': {'database_id': 'test_db_123'}
    }
    
    # Mock search response
    mock_search_response = Mock()
    mock_search_response.status_code = 200
    mock_search_response.json.return_value = {
        'results': [
            {
                'id': 'existing_db_789',
                'object': 'database',
                'title': [{'plain_text': 'Existing Database'}]
            }
        ],
        'has_more': False
    }
    
    # Mock update response
    mock_patch = Mock()
    mock_patch.return_value.status_code = 200
    mock_patch.return_value.json.return_value = {
        'id': 'test_page_456',
        'object': 'page',
        'properties': {'updated': True}
    }
    
    # Smart side effect for different endpoints
    def post_side_effect(*args, **kwargs):
        url = args[0] if args else kwargs.get('url', '')
        if 'databases' in url:
            return mock_database_response
        elif 'pages' in url:
            return mock_page_response
        elif 'search' in url:
            return mock_search_response
        else:
            return mock_page_response
    
    mock_post = Mock()
    mock_post.side_effect = post_side_effect
    
    return {
        'get': mock_get,
        'post': mock_post, 
        'patch': mock_patch,
        'search': mock_search_response
    }


def create_pipeline_orchestration_mock():
    """Create advanced pipeline orchestration mock."""
    
    mock_orchestrator = Mock()
    
    # Mock successful processing
    mock_orchestrator.process_captures.return_value = {
        "session_id": "orchestrated_session_123",
        "user_id": "test_user_456",
        "status": "completed",
        "processing_time": 2.5,
        "stages_completed": 5,
        "results_summary": {
            "captures_processed": 3,
            "concepts_extracted": 8,
            "knowledge_nodes_created": 15,
            "notion_pages_created": 2,
            "api_calls_optimized": 4
        },
        "batch_metrics": {
            "api_calls_made": 6,
            "api_calls_saved": 4,
            "batch_efficiency": 0.67,
            "cache_hit_rate": 0.33
        },
        "error_count": 0
    }
    
    # Mock status tracking
    mock_orchestrator.get_status.return_value = {
        "status": "operational",
        "active_sessions": 2,
        "queue_depth": 0,
        "last_error": None,
        "uptime": "2h 15m",
        "total_sessions_processed": 47
    }
    
    # Mock error scenarios
    def create_error_scenario(error_type):
        if error_type == "api_limit":
            return {
                "status": "failed", 
                "error": "API rate limit exceeded",
                "retry_after": 60,
                "partial_results": True
            }
        elif error_type == "database_connection":
            return {
                "status": "failed",
                "error": "Neo4j connection failed", 
                "stage": "knowledge_graph",
                "partial_results": True
            }
        elif error_type == "invalid_input":
            return {
                "status": "failed",
                "error": "Invalid input format",
                "stage": "capture_ingestion", 
                "partial_results": False
            }
    
    mock_orchestrator.create_error_scenario = create_error_scenario
    
    return mock_orchestrator


def create_node_step_by_step_mock():
    """Create detailed node-by-node execution mock."""
    
    # Capture Ingestion Node Mock
    capture_node_mock = Mock()
    capture_node_mock.prep.return_value = {
        "user_id": "test_user_123",
        "session_id": "step_session_456", 
        "captures_to_process": [
            {"content": "Test content 1", "title": "Title 1"},
            {"content": "Test content 2", "title": "Title 2"}
        ],
        "processing_config": {
            "html_cleaning": True,
            "content_validation": True,
            "metadata_extraction": True
        }
    }
    
    capture_node_mock.exec.return_value = {
        "processed_captures": [
            {
                "content": "Cleaned test content 1",
                "metadata": {"word_count": 15, "domain": "example.com"},
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "content": "Cleaned test content 2", 
                "metadata": {"word_count": 20, "domain": "test.com"},
                "timestamp": "2024-01-01T10:01:00Z"
            }
        ],
        "processing_summary": {
            "total_processed": 2,
            "successful": 2,
            "failed": 0,
            "warnings": []
        }
    }
    
    capture_node_mock.post.return_value = "default"
    
    # Content Analysis Node Mock
    analysis_node_mock = Mock()
    analysis_node_mock.prep.return_value = {
        "capture_categories": ["educational", "technical"],
        "batch_size": 2,
        "analysis_config": {
            "extract_concepts": True,
            "identify_topics": True, 
            "assess_complexity": True
        }
    }
    
    analysis_node_mock.exec.return_value = {
        "extracted_concepts": {
            "learning_concepts": ["machine learning", "data science"],
            "key_terms": {"ML": "Machine Learning technique"},
            "session_theme": "AI and Data Science",
            "complexity_assessment": {"level": "intermediate"}
        },
        "batch_metrics": {
            "api_calls_made": 1,
            "batches_processed": 1,
            "optimization_ratio": 0.5
        }
    }
    
    analysis_node_mock.post.return_value = "default"
    
    # Knowledge Graph Node Mock
    kg_node_mock = Mock() 
    kg_node_mock.prep.return_value = {
        "concepts": ["machine learning", "data science"],
        "entities": ["Python", "TensorFlow"],
        "neo4j_config": {"uri": "bolt://localhost:7687"}
    }
    
    kg_node_mock.exec.return_value = {
        "nodes_created": {"concepts": 5, "entities": 3},
        "relationships_created": 8,
        "graph_metrics": {"density": 0.45, "centrality": 0.67}
    }
    
    kg_node_mock.post.return_value = "default"
    
    return {
        "capture_ingestion": capture_node_mock,
        "content_analysis": analysis_node_mock,
        "knowledge_graph": kg_node_mock
    }


def create_error_scenario_mocks():
    """Create comprehensive error scenario mocks."""
    
    return {
        "api_timeout": {
            "error": "Request timeout",
            "details": "API call exceeded 30s timeout",
            "retry_suggested": True,
            "retry_after": 10
        },
        "invalid_credentials": {
            "error": "Authentication failed", 
            "details": "Invalid API key or token",
            "retry_suggested": False,
            "action_required": "Check credentials"
        },
        "rate_limit_exceeded": {
            "error": "Rate limit exceeded",
            "details": "Too many requests per minute",
            "retry_suggested": True,
            "retry_after": 60
        },
        "service_unavailable": {
            "error": "Service temporarily unavailable",
            "details": "External service is down",
            "retry_suggested": True,
            "retry_after": 300
        },
        "validation_error": {
            "error": "Input validation failed",
            "details": "Required fields missing or invalid format",
            "retry_suggested": False,
            "invalid_fields": ["user_id", "content"]
        },
        "processing_error": {
            "error": "Processing failed",
            "details": "Internal error during processing",
            "stage": "content_analysis",
            "partial_results": True
        },
        "notion_connection_failure": {
            "error": "Notion API connection failed",
            "details": "Unable to connect to Notion API",
            "status_code": 503,
            "retry_suggested": True,
            "retry_after": 30
        },
        "neo4j_connection_failure": {
            "error": "Neo4j connection failed",
            "details": "Database connection timeout",
            "stage": "knowledge_graph",
            "retry_suggested": True,
            "retry_after": 15
        },
        "llm_provider_error": {
            "error": "LLM provider unavailable",
            "details": "External LLM service is down",
            "fallback_available": True,
            "retry_suggested": True,
            "retry_after": 60
        }
    }


def create_performance_test_mock():
    """Create mock for performance testing scenarios."""
    
    def simulate_processing_time(items_count):
        """Simulate realistic processing times."""
        base_time = 0.1  # Base processing time
        per_item_time = 0.05  # Time per item
        return base_time + (items_count * per_item_time)
    
    mock_performance = Mock()
    
    # Small dataset performance
    mock_performance.process_small.return_value = {
        "items_processed": 5,
        "processing_time": simulate_processing_time(5),
        "memory_usage": "45MB",
        "api_calls": 2
    }
    
    # Large dataset performance  
    mock_performance.process_large.return_value = {
        "items_processed": 100,
        "processing_time": simulate_processing_time(100),
        "memory_usage": "180MB", 
        "api_calls": 8,
        "batch_optimizations": 12
    }
    
    # Concurrent processing
    mock_performance.process_concurrent.return_value = {
        "concurrent_sessions": 3,
        "total_items": 15,
        "processing_time": simulate_processing_time(15) * 0.7,  # Parallel efficiency
        "resource_contention": False
    }
    
    return mock_performance


def create_integration_test_helpers():
    """Create comprehensive integration test helpers."""
    
    def mock_sequential_node_execution():
        """Mock for testing sequential node execution patterns."""
        execution_log = []
        
        def log_execution(node_name, phase, result):
            execution_log.append({
                'node': node_name,
                'phase': phase,
                'timestamp': datetime.now().isoformat(),
                'success': 'error' not in result,
                'result_keys': list(result.keys()) if isinstance(result, dict) else []
            })
            return result
        
        return {
            'log_execution': log_execution,
            'get_execution_log': lambda: execution_log,
            'clear_log': lambda: execution_log.clear()
        }
    
    def create_edge_case_inputs():
        """Create edge case input scenarios for robust testing."""
        return {
            'empty_captures': [],
            'minimal_capture': [{
                'content': 'Short content',
                'user_id': 'test_user'
            }],
            'large_capture': [{
                'content': 'x' * 10000,  # Very long content
                'user_id': 'test_user',
                'title': 'Large Content Test'
            }],
            'special_characters': [{
                'content': 'Content with émojis 🤖 and spëciål chars',
                'user_id': 'test_user',
                'title': 'Special Chars Test'
            }],
            'missing_optional_fields': [{
                'content': 'Content without optional fields',
                'user_id': 'test_user'
            }]
        }
    
    return {
        'sequential_execution': mock_sequential_node_execution(),
        'edge_cases': create_edge_case_inputs()
    }


def create_fallback_behavior_mocks():
    """Create mocks for testing fallback behaviors."""
    
    def create_llm_fallback_mock():
        """Mock LLM client with controlled availability."""
        mock_client = Mock()
        mock_client._available = True
        
        def toggle_availability(available=None):
            if available is not None:
                mock_client._available = available
            return mock_client._available
        
        mock_client.is_available.side_effect = lambda: mock_client._available
        mock_client.toggle_availability = toggle_availability
        
        # Default responses
        mock_client.chat_completion.return_value = '{"fallback": "response"}'
        mock_client.get_provider_name.return_value = "test_provider"
        
        return mock_client
    
    def create_notion_api_fallback():
        """Mock Notion API with connection failure scenarios."""
        mock_api = Mock()
        mock_api._connection_status = 'healthy'
        
        def set_connection_status(status):
            """Status can be 'healthy', 'timeout', 'rate_limited', 'offline'"""
            mock_api._connection_status = status
        
        def mock_request_behavior(*args, **kwargs):
            if mock_api._connection_status == 'offline':
                raise ConnectionError("Connection failed")
            elif mock_api._connection_status == 'timeout':
                raise TimeoutError("Request timeout")
            elif mock_api._connection_status == 'rate_limited':
                response = Mock()
                response.status_code = 429
                response.json.return_value = {"error": "Rate limit exceeded"}
                return response
            else:
                response = Mock()
                response.status_code = 200
                response.json.return_value = {"id": "test_success"}
                return response
        
        mock_api.post.side_effect = mock_request_behavior
        mock_api.get.side_effect = mock_request_behavior  
        mock_api.patch.side_effect = mock_request_behavior
        mock_api.set_connection_status = set_connection_status
        
        return mock_api
    
    return {
        'llm_client': create_llm_fallback_mock(),
        'notion_api': create_notion_api_fallback()
    }


# Export all mock creators
__all__ = [
    'create_advanced_notion_mock',
    'create_pipeline_orchestration_mock', 
    'create_node_step_by_step_mock',
    'create_error_scenario_mocks',
    'create_performance_test_mock',
    'create_integration_test_helpers',
    'create_fallback_behavior_mocks'
]