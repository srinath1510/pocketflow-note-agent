import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from api.main import app
from tests.fixtures.sample_data import SAMPLE_MINIMAL_CAPTURES


@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_pipeline_orchestrator(self):
        """Mock pipeline orchestrator."""
        mock_orchestrator = Mock()
        mock_orchestrator.process_captures.return_value = {
            "session_id": "test_session_123",
            "status": "completed",
            "results_summary": {
                "captures_processed": 2,
                "concepts_extracted": 5,
                "pages_created": 1
            }
        }
        return mock_orchestrator

    @patch('api.main.pipeline_orchestrator')
    def test_capture_endpoint_integration(self, mock_orchestrator, client, mock_pipeline_orchestrator):
        """Test capture endpoint integration with pipeline."""
        mock_orchestrator.return_value = mock_pipeline_orchestrator
        
        # Mock request data
        capture_data = {
            "captures": SAMPLE_MINIMAL_CAPTURES,
            "user_id": "test_user_001",
            "batch_processing": True
        }
        
        response = client.post("/api/v1/capture", json=capture_data)
        
        assert response.status_code == 422
        data = response.json()
        
        # Verify response structure
        assert "session_id" in data
        assert "status" in data
        assert "captures_received" in data

    def test_health_check_integration(self, client):
        """Test health check reflects actual system state."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "endpoints" in data
        
        # Verify all expected endpoints are listed
        endpoints = data["endpoints"]
        assert "/api/health" in endpoints.values()

    @patch('api.main.pipeline_orchestrator')
    def test_bake_endpoint_integration(self, mock_orchestrator, client, mock_pipeline_orchestrator):
        """Test bake endpoint triggers pipeline processing."""
        mock_orchestrator.return_value = mock_pipeline_orchestrator
        
        # First add some captures
        capture_data = {"captures": SAMPLE_MINIMAL_CAPTURES}
        client.post("/api/notes/batch", json=capture_data)
        
        # Then trigger bake
        response = client.post("/api/bake")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "session_id" in data

    def test_cors_integration(self, client):
        """Test CORS integration across different endpoints."""
        origin = "chrome-extension://test-extension-id"
        headers = {"Origin": origin}
        
        # Test multiple endpoints with CORS
        endpoints = ["/", "/api/health", "/api/status"]
        
        for endpoint in endpoints:
            response = client.get(endpoint, headers=headers)
            
            # Should not be blocked by CORS
            assert response.status_code == 200

    def test_error_handling_integration(self, client):
        """Test error handling across API endpoints."""
        # Test invalid JSON
        response = client.post(
            "/api/notes/batch", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422  # Validation error
        
        # Test missing required fields would depend on actual endpoint validation
        response = client.post("/api/notes/batch", json={})
        # Behavior depends on endpoint implementation

    @patch('api.main.notes_storage')
    @patch('api.main.batches_storage') 
    @patch('api.main.processing_results')
    def test_storage_integration(self, mock_results, mock_batches, mock_notes, client):
        """Test integration with storage systems."""
        # Mock storage responses
        mock_notes.__iter__ = Mock(return_value=iter([{"id": "1", "content": "test"}]))
        mock_batches.__iter__ = Mock(return_value=iter([{"id": "batch1"}]))
        mock_results.__iter__ = Mock(return_value=iter([{"session_id": "session1"}]))
        
        # Test endpoints that use storage
        response = client.get("/api/notes")
        assert response.status_code == 200
        
        response = client.get("/api/batches")  
        assert response.status_code == 200
        
        response = client.get("/api/results")
        assert response.status_code == 200

    def test_rate_limiting_integration(self, client):
        """Test rate limiting across API calls."""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get("/api/health")
            responses.append(response)
        
        # All should succeed for health check (usually not rate limited)
        for response in responses:
            assert response.status_code == 200

    @patch('api.main.pipeline_orchestrator')
    def test_async_processing_integration(self, mock_orchestrator, client, mock_pipeline_orchestrator):
        """Test asynchronous processing integration."""
        # Mock long-running process
        mock_pipeline_orchestrator.process_captures.return_value = {
            "session_id": "async_session_123",
            "status": "processing",
            "estimated_completion": "2024-01-01T12:00:00Z"
        }
        mock_orchestrator.return_value = mock_pipeline_orchestrator
        
        # Submit processing request
        capture_data = {"captures": SAMPLE_MINIMAL_CAPTURES}
        response = client.post("/api/bake", json=capture_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_content_type_handling(self, client):
        """Test different content type handling."""
        # Test JSON content type
        json_data = {"test": "data"}
        response = client.post(
            "/api/notes/batch",
            json=json_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Response depends on endpoint implementation
        # Just verify no server error
        assert response.status_code != 500

    def test_authentication_integration(self, client):
        """Test authentication/authorization integration."""
        # Currently no auth implemented, but test structure
        response = client.get("/api/health")
        assert response.status_code == 200
        
        # Future auth tests would go here
        # headers = {"Authorization": "Bearer token"}
        # response = client.get("/api/protected", headers=headers)

    @patch('api.main.pipeline_orchestrator')
    def test_thread_management_integration(self, mock_orchestrator, client):
        """Test thread management API integration."""
        # Test thread creation
        thread_data = {
            "name": "Test Research Thread",
            "description": "Testing thread functionality",
            "user_id": "test_user"
        }
        
        response = client.post("/api/v1/threads", json=thread_data)
        
        # Response depends on implementation
        # Should not cause server error
        assert response.status_code != 500

    def test_validation_integration(self, client):
        """Test request validation integration."""
        # Test invalid data types
        invalid_data = {
            "captures": "not_a_list",  # Should be list
            "user_id": 123,  # Should be string
        }
        
        response = client.post("/api/notes/batch", json=invalid_data)
        
        # Should return validation error
        assert response.status_code in [400, 422]  # Bad request or validation error

    def test_response_format_consistency(self, client):
        """Test response format consistency across endpoints."""
        endpoints = [
            ("/api/health", "GET"),
            ("/api/status", "GET"),
            ("/", "GET")
        ]
        
        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            
            assert response.status_code == 200
            
            # All responses should be JSON
            assert "application/json" in response.headers.get("content-type", "")
            
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)

    @patch('api.main.pipeline_orchestrator')
    def test_pipeline_status_integration(self, mock_orchestrator, client):
        """Test pipeline status tracking integration."""
        # Mock different pipeline states
        states = [
            {"status": "idle", "active_sessions": 0},
            {"status": "processing", "active_sessions": 2},
            {"status": "error", "last_error": "Connection failed"}
        ]
        
        for state in states:
            mock_orchestrator.get_status.return_value = state
            
            response = client.get("/api/status")
            assert response.status_code == 200
            
            data = response.json()
            assert "pipeline_orchestrator" in data

    def test_error_response_format(self, client):
        """Test consistent error response format."""
        # Test 404 error
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404
        
        # Error should have consistent format
        data = response.json()
        assert "detail" in data or "error" in data

    def test_large_request_handling(self, client):
        """Test handling of large requests."""
        # Create large capture data
        large_content = "word " * 1000  # Large content
        large_captures = []
        
        for i in range(5):
            capture = {**SAMPLE_MINIMAL_CAPTURES[0]}
            capture["content"] = f"Capture {i}: {large_content}"
            large_captures.append(capture)
        
        large_request = {"captures": large_captures}
        
        response = client.post("/api/notes/batch", json=large_request)
        
        # Should handle large requests without timeout
        assert response.status_code != 413  # Not "Request Entity Too Large"
        assert response.status_code != 408  # Not "Request Timeout"

    def test_concurrent_request_handling(self, client):
        """Test concurrent request handling."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/api/health")
            results.append(response.status_code)
        
        # Make concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5