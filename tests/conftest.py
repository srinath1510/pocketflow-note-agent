import pytest
import os
import tempfile
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.pipeline_config import PipelineConfig


@pytest.fixture(scope="session")
def test_config():
    """Test configuration that doesn't require real credentials."""
    with patch.dict(os.environ, {
        'NEO4J_URI': 'bolt://localhost:7687',
        'NEO4J_USER': 'test_user',
        'NEO4J_PASSWORD': 'test_password',
        'ANTHROPIC_API_KEY': 'test_anthropic_key',
        'NOTION_TOKEN': 'test_notion_token',
        'LLM_PROVIDER': 'anthropic'
    }):
        yield PipelineConfig()


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver and session."""
    mock_driver = Mock()
    mock_session = Mock()
    mock_result = Mock()
    mock_record = Mock()
    
    mock_record.get.return_value = "test_value"
    mock_record.__getitem__ = Mock(return_value="test_value")
    mock_result.single.return_value = mock_record
    mock_result.__iter__ = Mock(return_value=iter([mock_record]))
    mock_session.run.return_value = mock_result
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_driver.session.return_value.__exit__.return_value = None
    
    with patch('neo4j.GraphDatabase.driver', return_value=mock_driver):
        yield mock_driver


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Test LLM response")]
    mock_client.messages.create.return_value = mock_response
    
    with patch('anthropic.Anthropic', return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_notion_client():
    """Mock Notion client."""
    mock_client = Mock()
    
    # Mock API responses
    mock_client.create_database.return_value = "test_database_id"
    mock_client.create_page.return_value = {
        'id': 'test_page_id',
        'url': 'https://notion.so/test_page_id'
    }
    mock_client.search_database_by_title.return_value = None
    mock_client.update_page.return_value = {'id': 'test_page_id'}
    
    yield mock_client


@pytest.fixture
def sample_minimal_input():
    """Sample minimal capture input for testing."""
    return [
        {
            "content": "Machine learning is a method of data analysis that automates analytical model building.",
            "user_id": "test_user_123",
            "source_url": "https://example.com/ml-basics",
            "title": "Machine Learning Fundamentals",
            "intent": "learn",
            "user_note": "Important concept for AI course"
        },
        {
            "content": "Neural networks are computing systems inspired by biological neural networks.",
            "user_id": "test_user_123", 
            "source_url": "https://example.com/neural-networks",
            "title": "Introduction to Neural Networks",
            "intent": "research"
        }
    ]


@pytest.fixture
def sample_processed_capture():
    """Sample processed capture data."""
    return {
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "content": "Machine learning fundamentals including supervised and unsupervised learning.",
        "title": "ML Basics",
        "source_url": "https://example.com/ml",
        "timestamp": "2024-01-01T00:00:00Z",
        "metadata": {
            "word_count": 150,
            "domain": "example.com",
            "content_category": "educational",
            "knowledge_level": "beginner",
            "reading_time_minutes": 3
        }
    }


@pytest.fixture
def sample_extracted_concepts():
    """Sample extracted concepts data."""
    return {
        "learning_concepts": ["machine learning", "neural networks", "supervised learning"],
        "key_terms": {
            "machine learning": "Method of data analysis that automates model building",
            "neural networks": "Computing systems inspired by biological neurons"
        },
        "entities": {
            "technologies": ["Python", "TensorFlow", "scikit-learn"],
            "concepts": ["algorithm", "model", "training"]
        },
        "topics": ["artificial intelligence", "data science", "computer science"],
        "session_theme": "machine learning fundamentals",
        "complexity_assessment": {
            "overall_level": "intermediate",
            "technical_depth": "moderate",
            "prerequisite_knowledge": ["programming", "mathematics"]
        },
        "knowledge_progression": ["data", "algorithms", "machine learning", "neural networks"]
    }


@pytest.fixture
def sample_shared_state(sample_processed_capture, sample_extracted_concepts):
    """Sample shared state for pipeline testing."""
    return {
        "session_id": "test_session_456",
        "user_id": "test_user_123",
        "raw_captures": [sample_processed_capture],
        "extracted_concepts": sample_extracted_concepts,
        "pipeline_metadata": {
            "status": "in_progress",
            "current_stage": "test",
            "start_time": "2024-01-01T00:00:00Z"
        }
    }


@pytest.fixture
def temp_directory():
    """Temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with patch('pathlib.Path.mkdir'), \
         patch('pathlib.Path.write_text'), \
         patch('pathlib.Path.read_text', return_value='test content'), \
         patch('pathlib.Path.exists', return_value=True):
        yield


@pytest.fixture
def mock_requests():
    """Mock requests library for API calls."""
    mock_response = Mock()
    mock_response.json.return_value = {"status": "success", "data": {}}
    mock_response.status_code = 200
    mock_response.text = '{"status": "success"}'
    
    with patch('requests.get', return_value=mock_response), \
         patch('requests.post', return_value=mock_response), \
         patch('requests.patch', return_value=mock_response):
        yield mock_response


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment after each test."""
    yield
    # Cleanup any test artifacts
    for key in list(os.environ.keys()):
        if key.startswith('TEST_'):
            del os.environ[key]


@pytest.fixture
def disable_external_calls():
    """Disable all external API calls during testing."""
    with patch('anthropic.Anthropic'), \
         patch('requests.get'), \
         patch('requests.post'), \
         patch('neo4j.GraphDatabase.driver'):
        yield


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)