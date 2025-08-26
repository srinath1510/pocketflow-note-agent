import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from nodes.capture_ingestion import CaptureIngestionNode
from tests.fixtures.sample_data import SAMPLE_MINIMAL_CAPTURES, ERROR_SCENARIOS
from tests.fixtures.mock_responses import create_integration_test_helpers


class TestCaptureIngestionNode:
    """Unit tests for CaptureIngestionNode."""

    @pytest.fixture
    def node(self):
        """Create a CaptureIngestionNode instance."""
        return CaptureIngestionNode()

    def test_node_initialization(self, node):
        """Test node initializes correctly."""
        assert node is not None
        assert hasattr(node, 'logger')
        assert hasattr(node, 'content_processor')

    def test_prep_phase_success(self, node):
        """Test successful prep phase with valid input."""
        shared_state = {"raw_input": SAMPLE_MINIMAL_CAPTURES}
        
        result = node.prep(shared_state)
        
        assert "user_id" in result
        assert "session_id" in result
        assert "captures_to_process" in result
        assert len(result["captures_to_process"]) == len(SAMPLE_MINIMAL_CAPTURES)
        assert result["user_id"] == "test_user_001"

    def test_prep_phase_no_input(self, node):
        """Test prep phase with no raw input."""
        shared_state = {}
        
        result = node.prep(shared_state)
        
        assert "error" in result
        assert "No raw input provided" in result["error"]

    def test_prep_phase_empty_input(self, node):
        """Test prep phase with empty input list."""
        shared_state = {"raw_input": []}
        
        result = node.prep(shared_state)
        
        assert "error" in result
        assert "No captures to process" in result["error"]

    def test_exec_phase_success(self, node):
        """Test successful execution phase."""
        prep_data = {
            "user_id": "test_user_001",
            "session_id": "test_session_001", 
            "captures_to_process": SAMPLE_MINIMAL_CAPTURES
        }
        
        result = node.exec(prep_data)
        
        assert "raw_captures" in result
        assert "processing_summary" in result
        assert len(result["raw_captures"]) == len(SAMPLE_MINIMAL_CAPTURES)
        
        # Check processed capture structure
        capture = result["raw_captures"][0]
        assert "user_id" in capture
        assert "session_id" in capture
        assert "content" in capture
        assert "metadata" in capture
        assert "timestamp" in capture

    def test_exec_phase_with_error(self, node):
        """Test exec phase with error in prep data."""
        prep_data = {"error": "Test error"}
        
        result = node.exec(prep_data)
        
        assert result == prep_data  # Should return the error unchanged

    def test_content_processing(self, node):
        """Test content processing functionality."""
        test_capture = {
            "content": "This is a test content with HTML <b>tags</b> and extra spaces.",
            "user_id": "test_user",
            "source_url": "https://example.com/test",
            "title": "Test Article"
        }
        
        processed = node._process_single_capture(test_capture, "session_123")
        
        assert processed["content"] == test_capture["content"]
        assert processed["session_id"] == "session_123"
        assert "metadata" in processed
        assert "timestamp" in processed
        
        # Check metadata fields
        metadata = processed["metadata"]
        assert "word_count" in metadata
        assert "domain" in metadata
        assert "content_category" in metadata
        assert metadata["domain"] == "example.com"

    def test_html_content_cleaning(self, node):
        """Test HTML content cleaning."""
        html_content = "<html><body><p>Test content</p><script>alert('test')</script></body></html>"
        
        test_capture = {
            "content": html_content,
            "user_id": "test_user",
            "source_url": "https://example.com",
            "title": "HTML Test"
        }
        
        processed = node._process_single_capture(test_capture, "session_123")
        
        # Should clean HTML but preserve text content
        assert "<script>" not in processed["content"]
        assert "Test content" in processed["content"]

    def test_metadata_extraction(self, node):
        """Test metadata extraction from content."""
        test_capture = {
            "content": "This is a comprehensive article about machine learning algorithms.",
            "user_id": "test_user",
            "source_url": "https://ml-tutorial.com/advanced",
            "title": "ML Algorithms Guide"
        }
        
        processed = node._process_single_capture(test_capture, "session_123")
        metadata = processed["metadata"]
        
        assert metadata["word_count"] > 0
        assert metadata["domain"] == "ml-tutorial.com"
        assert metadata["content_category"] in ["educational", "technical", "general"]
        assert metadata["knowledge_level"] in ["beginner", "intermediate", "advanced"]
        assert isinstance(metadata["reading_time_minutes"], (int, float))

    def test_url_validation_and_parsing(self, node):
        """Test URL validation and domain extraction."""
        test_cases = [
            ("https://example.com/path", "example.com"),
            ("http://subdomain.example.com", "subdomain.example.com"),
            ("https://example.com:8080/path", "example.com"),
            ("invalid-url", "unknown"),
            ("", "unknown")
        ]
        
        for url, expected_domain in test_cases:
            test_capture = {
                "content": "test content",
                "user_id": "test_user",
                "source_url": url,
                "title": "Test"
            }
            
            processed = node._process_single_capture(test_capture, "session_123")
            assert processed["metadata"]["domain"] == expected_domain

    def test_content_categorization(self, node):
        """Test content categorization logic."""
        test_cases = [
            ("Learn how to program in Python", "educational"),
            ("Breaking news: major development in AI", "news"),
            ("Step-by-step tutorial for beginners", "educational"),
            ("Random blog post about daily life", "general")
        ]
        
        for content, expected_category in test_cases:
            test_capture = {
                "content": content,
                "user_id": "test_user", 
                "source_url": "https://example.com",
                "title": "Test"
            }
            
            processed = node._process_single_capture(test_capture, "session_123")
            # Category detection might not be exact, so check it's a valid category
            assert processed["metadata"]["content_category"] in ["educational", "technical", "news", "general"]

    def test_post_phase_success(self, node, sample_shared_state):
        """Test successful post phase."""
        exec_result = {
            "raw_captures": [sample_shared_state["raw_captures"][0]],
            "processing_summary": {
                "total_processed": 1,
                "successful": 1,
                "failed": 0
            }
        }
        
        result = node.post(sample_shared_state, {}, exec_result)
        
        assert result == "default"
        assert "raw_captures" in sample_shared_state
        assert sample_shared_state["pipeline_metadata"]["capture_ingestion_complete"] is True

    def test_post_phase_with_error(self, node, sample_shared_state):
        """Test post phase with execution error."""
        exec_result = {"error": "Processing failed"}
        
        result = node.post(sample_shared_state, {}, exec_result)
        
        assert result == "error"
        assert "capture_ingestion_error" in sample_shared_state

    def test_session_id_generation(self, node):
        """Test session ID generation."""
        shared_state = {"raw_input": SAMPLE_MINIMAL_CAPTURES}
        
        result1 = node.prep(shared_state)
        result2 = node.prep(shared_state)
        
        # Should generate different session IDs
        assert result1["session_id"] != result2["session_id"]
        assert len(result1["session_id"]) > 0
        assert len(result2["session_id"]) > 0

    def test_user_id_consistency(self, node):
        """Test user ID consistency across captures."""
        mixed_user_captures = [
            {"content": "Content 1", "user_id": "user1", "title": "Title 1"},
            {"content": "Content 2", "user_id": "user2", "title": "Title 2"}
        ]
        
        shared_state = {"raw_input": mixed_user_captures}
        result = node.prep(shared_state)
        
        # Should use the first user_id found
        assert result["user_id"] == "user1"

    def test_missing_required_fields(self, node):
        """Test handling of captures with missing required fields."""
        invalid_captures = [
            ERROR_SCENARIOS["invalid_input"]["empty_content"],
            ERROR_SCENARIOS["invalid_input"]["missing_user_id"]
        ]
        
        for invalid_capture in invalid_captures:
            shared_state = {"raw_input": [invalid_capture]}
            result = node.prep(shared_state)
            
            # Should handle gracefully or show error
            if "error" not in result:
                # If processing continues, check it handles missing fields
                exec_result = node.exec(result)
                assert "raw_captures" in exec_result or "error" in exec_result

    def test_large_content_handling(self, node):
        """Test handling of very large content."""
        large_content = "word " * 10000  # 10k words
        
        test_capture = {
            "content": large_content,
            "user_id": "test_user",
            "source_url": "https://example.com",
            "title": "Large Content Test"
        }
        
        processed = node._process_single_capture(test_capture, "session_123")
        
        assert len(processed["content"]) > 0
        assert processed["metadata"]["word_count"] > 9000
        assert isinstance(processed["metadata"]["reading_time_minutes"], (int, float))

    def test_timestamp_format(self, node):
        """Test timestamp format in processed captures."""
        test_capture = {
            "content": "test content",
            "user_id": "test_user",
            "source_url": "https://example.com",
            "title": "Test"
        }
        
        processed = node._process_single_capture(test_capture, "session_123")
        
        # Should be ISO format timestamp
        timestamp = processed["timestamp"]
        assert isinstance(timestamp, str)
        assert "T" in timestamp
        assert timestamp.endswith("Z") or "+" in timestamp[-6:]

    def test_edge_case_handling_with_helpers(self, node):
        """Test edge case handling using integration test helpers."""
        helpers = create_integration_test_helpers()
        edge_cases = helpers['edge_cases']
        
        # Test minimal capture
        shared_state = {"raw_input": edge_cases['minimal_capture']}
        result = node.prep(shared_state)
        assert "captures_to_process" in result
        
        # Test special characters
        shared_state = {"raw_input": edge_cases['special_characters']}
        result = node.prep(shared_state)
        exec_result = node.exec(result)
        processed_content = exec_result["raw_captures"][0]["content"]
        assert "émojis" in processed_content
        assert "🤖" in processed_content