import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from nodes.content_analysis import ContentAnalysisNode
from tests.fixtures.sample_data import SAMPLE_PROCESSED_CAPTURES, SAMPLE_EXTRACTED_CONCEPTS


class TestContentAnalysisNode:
    """Unit tests for ContentAnalysisNode."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing."""
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client.get_provider_name.return_value = "test_provider"
        mock_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        return mock_client

    @pytest.fixture
    def node_with_mock(self, mock_llm_client):
        """Create a ContentAnalysisNode with mocked LLM client."""
        with patch('nodes.content_analysis.get_llm_client', return_value=mock_llm_client):
            node = ContentAnalysisNode()
            return node

    def test_node_initialization(self, node_with_mock):
        """Test node initializes correctly."""
        assert node_with_mock is not None
        assert hasattr(node_with_mock, 'logger')
        assert hasattr(node_with_mock, 'llm_client')

    def test_prep_phase_success(self, node_with_mock):
        """Test successful prep phase."""
        shared_state = {"raw_captures": SAMPLE_PROCESSED_CAPTURES}
        
        result = node_with_mock.prep(shared_state)
        
        assert "capture_categories" in result
        assert "batch_config" in result
        assert "llm_provider" in result
        assert result["llm_provider"] == "test_provider"

    def test_prep_phase_no_captures(self, node_with_mock):
        """Test prep phase with no processed captures."""
        shared_state = {}
        
        result = node_with_mock.prep(shared_state)
        
        assert "error" in result
        assert "No captures to analyze" in result["error"]

    def test_exec_phase_success(self, node_with_mock):
        """Test successful execution phase."""
        prep_data = {
            "capture_categories": {
                "llm_required": SAMPLE_PROCESSED_CAPTURES,
                "rule_based": [],
                "cached": []
            },
            "batch_config": {
                "total_captures": len(SAMPLE_PROCESSED_CAPTURES),
                "llm_required": len(SAMPLE_PROCESSED_CAPTURES),
                "estimated_api_calls": 1
            }
        }
        
        result = node_with_mock.exec(prep_data)
        
        assert "extracted_concepts" in result
        assert "batch_metrics" in result

    def test_exec_phase_with_error(self, node_with_mock):
        """Test exec phase with error in prep data."""
        prep_data = {"error": "Test error"}
        
        result = node_with_mock.exec(prep_data)
        
        assert "error" in result
        assert result["error"] == "Test error"

    def test_post_phase_success(self, node_with_mock):
        """Test successful post phase."""
        shared_state = {"pipeline_metadata": {}}
        
        exec_result = {
            "extracted_concepts": SAMPLE_EXTRACTED_CONCEPTS,
            "batch_metrics": {"api_calls_saved": 5}
        }
        
        result = node_with_mock.post(shared_state, {}, exec_result)
        
        assert result == "default"
        assert "extracted_concepts" in shared_state

    def test_llm_initialization_failure(self):
        """Test LLM initialization failure handling."""
        with patch('nodes.content_analysis.get_llm_client') as mock_get_client:
            mock_get_client.side_effect = Exception("API key not found")
            
            with pytest.raises(RuntimeError, match="No LLM providers available"):
                ContentAnalysisNode()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])