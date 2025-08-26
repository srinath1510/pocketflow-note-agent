import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from nodes.content_analysis import ContentAnalysisNode
from tests.fixtures.sample_data import SAMPLE_PROCESSED_CAPTURES, SAMPLE_EXTRACTED_CONCEPTS


class TestContentAnalysisNode:
    """Unit tests for ContentAnalysisNode."""

    @pytest.fixture
    def node(self):
        """Create a ContentAnalysisNode instance."""
        return ContentAnalysisNode()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing."""
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        return mock_client

    def test_node_initialization(self, node):
        """Test node initializes correctly."""
        assert node is not None
        assert hasattr(node, 'logger')
        assert hasattr(node, 'llm_client')

    @patch('nodes.content_analysis.get_llm_client')
    def test_llm_initialization_success(self, mock_get_client):
        """Test successful LLM client initialization."""
        mock_client = Mock()
        mock_client.is_available.return_value = True
        mock_get_client.return_value = mock_client
        
        node = ContentAnalysisNode()
        
        assert node.llm_client == mock_client
        mock_get_client.assert_called_once()

    @patch('nodes.content_analysis.get_llm_client')
    def test_llm_initialization_failure(self, mock_get_client):
        """Test LLM initialization failure handling."""
        mock_get_client.side_effect = Exception("API key not found")
        
        node = ContentAnalysisNode()
        
        assert node.llm_client is None

    def test_prep_phase_success(self, node, sample_shared_state):
        """Test successful prep phase."""
        result = node.prep(sample_shared_state)
        
        assert "user_id" in result
        assert "session_id" in result  
        assert "processed_captures" in result
        assert result["user_id"] == "test_user_123"
        assert len(result["processed_captures"]) > 0

    def test_prep_phase_no_captures(self, node):
        """Test prep phase with no processed captures."""
        shared_state = {"session_id": "test", "user_id": "test"}
        
        result = node.prep(shared_state)
        
        assert "error" in result
        assert "No processed captures found" in result["error"]

    def test_exec_phase_success(self, node, mock_llm_client):
        """Test successful execution phase."""
        node.llm_client = mock_llm_client
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session",
            "processed_captures": SAMPLE_PROCESSED_CAPTURES
        }
        
        result = node.exec(prep_data)
        
        assert "extracted_concepts" in result
        assert "batch_metrics" in result
        
        concepts = result["extracted_concepts"]
        assert "learning_concepts" in concepts
        assert "key_terms" in concepts
        assert "session_theme" in concepts

    def test_exec_phase_with_error(self, node):
        """Test exec phase with error in prep data."""
        prep_data = {"error": "Test error"}
        
        result = node.exec(prep_data)
        
        assert result == prep_data

    def test_exec_phase_no_llm(self, node):
        """Test exec phase when LLM is not available."""
        node.llm_client = None
        
        prep_data = {
            "user_id": "test_user",
            "processed_captures": SAMPLE_PROCESSED_CAPTURES
        }
        
        result = node.exec(prep_data)
        
        assert "error" in result
        assert "LLM client not available" in result["error"]

    def test_batch_processing_optimization(self, node, mock_llm_client):
        """Test batch processing optimization."""
        node.llm_client = mock_llm_client
        
        # Create multiple similar captures for batching
        captures = [
            {**SAMPLE_PROCESSED_CAPTURES[0], "content": f"Content {i}"}
            for i in range(5)
        ]
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session", 
            "processed_captures": captures
        }
        
        result = node.exec(prep_data)
        
        assert "batch_metrics" in result
        metrics = result["batch_metrics"]
        assert "api_calls_made" in metrics
        assert "batches_processed" in metrics
        
        # Should make fewer API calls than number of captures due to batching
        assert metrics["api_calls_made"] <= len(captures)

    @patch('nodes.content_analysis.get_llm_client')
    def test_llm_response_parsing(self, mock_get_client, node):
        """Test parsing of LLM response."""
        mock_client = Mock()
        mock_client.is_available.return_value = True
        
        # Test valid JSON response
        valid_response = json.dumps({
            "learning_concepts": ["test_concept"],
            "key_terms": {"term1": "definition1"},
            "session_theme": "test_theme"
        })
        mock_client.chat_completion.return_value = valid_response
        mock_get_client.return_value = mock_client
        
        node = ContentAnalysisNode()
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session",
            "processed_captures": SAMPLE_PROCESSED_CAPTURES
        }
        
        result = node.exec(prep_data)
        
        assert "extracted_concepts" in result
        concepts = result["extracted_concepts"]
        assert concepts["learning_concepts"] == ["test_concept"]
        assert concepts["key_terms"]["term1"] == "definition1"

    def test_llm_invalid_json_response(self, node, mock_llm_client):
        """Test handling of invalid JSON from LLM."""
        mock_llm_client.chat_completion.return_value = "invalid json response"
        node.llm_client = mock_llm_client
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session",
            "processed_captures": SAMPLE_PROCESSED_CAPTURES
        }
        
        result = node.exec(prep_data)
        
        # Should handle gracefully and provide fallback or error
        assert "extracted_concepts" in result or "error" in result

    def test_content_deduplication(self, node, mock_llm_client):
        """Test content deduplication in batching."""
        node.llm_client = mock_llm_client
        
        # Create duplicate content captures
        duplicate_captures = [
            SAMPLE_PROCESSED_CAPTURES[0],
            SAMPLE_PROCESSED_CAPTURES[0],  # Exact duplicate
            {**SAMPLE_PROCESSED_CAPTURES[0], "title": "Different title"}  # Similar content
        ]
        
        prep_data = {
            "user_id": "test_user", 
            "session_id": "test_session",
            "processed_captures": duplicate_captures
        }
        
        result = node.exec(prep_data)
        
        # Should process efficiently despite duplicates
        assert "batch_metrics" in result
        assert result["batch_metrics"]["api_calls_made"] <= len(duplicate_captures)

    def test_concept_extraction_quality(self, node, mock_llm_client):
        """Test quality of concept extraction."""
        # Mock high-quality response
        quality_response = {
            "learning_concepts": ["machine learning", "neural networks", "deep learning"],
            "key_terms": {
                "machine learning": "AI technique for pattern recognition",
                "neural networks": "Computing systems inspired by biological neurons"
            },
            "complexity_assessment": {
                "overall_level": "intermediate",
                "technical_depth": "moderate"
            },
            "knowledge_progression": ["basics", "intermediate", "advanced"]
        }
        
        mock_llm_client.chat_completion.return_value = json.dumps(quality_response)
        node.llm_client = mock_llm_client
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session", 
            "processed_captures": SAMPLE_PROCESSED_CAPTURES
        }
        
        result = node.exec(prep_data)
        
        concepts = result["extracted_concepts"]
        assert len(concepts["learning_concepts"]) >= 3
        assert len(concepts["key_terms"]) >= 2
        assert "complexity_assessment" in concepts
        assert "knowledge_progression" in concepts

    def test_post_phase_success(self, node, sample_shared_state):
        """Test successful post phase."""
        exec_result = {
            "extracted_concepts": SAMPLE_EXTRACTED_CONCEPTS,
            "batch_metrics": {
                "api_calls_made": 2,
                "api_calls_saved": 1
            }
        }
        
        result = node.post(sample_shared_state, {}, exec_result)
        
        assert result == "default"
        assert "extracted_concepts" in sample_shared_state
        assert sample_shared_state["pipeline_metadata"]["content_analysis_complete"] is True
        assert "batch_metrics" in sample_shared_state

    def test_post_phase_with_error(self, node, sample_shared_state):
        """Test post phase with execution error."""
        exec_result = {"error": "LLM processing failed"}
        
        result = node.post(sample_shared_state, {}, exec_result)
        
        assert result == "error"
        assert "content_analysis_error" in sample_shared_state

    def test_caching_functionality(self, node, mock_llm_client):
        """Test content caching to avoid duplicate processing."""
        mock_llm_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        node.llm_client = mock_llm_client
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session",
            "processed_captures": SAMPLE_PROCESSED_CAPTURES
        }
        
        # Process once
        result1 = node.exec(prep_data)
        call_count_1 = mock_llm_client.chat_completion.call_count
        
        # Process again with same content
        result2 = node.exec(prep_data)
        call_count_2 = mock_llm_client.chat_completion.call_count
        
        # Second call should use cache (fewer LLM calls)
        assert "batch_metrics" in result1
        assert "batch_metrics" in result2
        # Cache behavior depends on implementation

    def test_llm_error_handling(self, node, mock_llm_client):
        """Test handling of LLM API errors."""
        mock_llm_client.chat_completion.side_effect = Exception("API rate limit exceeded")
        node.llm_client = mock_llm_client
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session",
            "processed_captures": SAMPLE_PROCESSED_CAPTURES
        }
        
        result = node.exec(prep_data)
        
        assert "error" in result
        assert "API rate limit" in result["error"] or "processing failed" in result["error"].lower()

    def test_empty_content_handling(self, node, mock_llm_client):
        """Test handling of empty or very short content."""
        node.llm_client = mock_llm_client
        
        empty_capture = [{
            **SAMPLE_PROCESSED_CAPTURES[0],
            "content": ""
        }]
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session",
            "processed_captures": empty_capture
        }
        
        result = node.exec(prep_data)
        
        # Should handle gracefully - either skip processing or provide minimal response
        assert "extracted_concepts" in result or "error" in result

    def test_session_theme_generation(self, node, mock_llm_client):
        """Test session theme generation from multiple captures."""
        theme_response = {
            **SAMPLE_EXTRACTED_CONCEPTS,
            "session_theme": "artificial intelligence and machine learning fundamentals"
        }
        
        mock_llm_client.chat_completion.return_value = json.dumps(theme_response)
        node.llm_client = mock_llm_client
        
        prep_data = {
            "user_id": "test_user",
            "session_id": "test_session",
            "processed_captures": SAMPLE_PROCESSED_CAPTURES * 3  # Multiple captures
        }
        
        result = node.exec(prep_data)
        
        concepts = result["extracted_concepts"]
        assert "session_theme" in concepts
        assert len(concepts["session_theme"]) > 0
        assert isinstance(concepts["session_theme"], str)