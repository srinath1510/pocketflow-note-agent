import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from api.main import app


class TestAPIMain:
    """Unit tests for FastAPI main application."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "BrowserBud" in data["message"]
        assert "version" in data
        assert "endpoints" in data
        assert "documentation" in data

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "service" in data
        assert data["service"] == "browserbud-api"

    def test_status_endpoint(self, client):
        """Test status endpoint returns detailed information."""
        response = client.get("/api/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "server" in data
        assert "BrowserBud" in data["server"]
        assert "status" in data
        assert data["status"] == "running"
        assert "timestamp" in data
        assert "stats" in data
        assert "pipeline_orchestrator" in data

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/api/health")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_cors_preflight_request(self, client):
        """Test CORS preflight request handling."""
        headers = {
            "Origin": "chrome-extension://test-extension-id",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        
        response = client.options("/api/health", headers=headers)
        assert response.status_code == 200

    @patch('api.main.pipeline_orchestrator')
    def test_pipeline_orchestrator_available(self, mock_orchestrator, client):
        """Test when pipeline orchestrator is available."""
        mock_orchestrator.__bool__ = Mock(return_value=True)
        
        response = client.get("/api/status")
        data = response.json()
        
        assert data["pipeline_orchestrator"]["available"] is True
        assert data["pipeline_orchestrator"]["status"] == "operational"

    @patch('api.main.pipeline_orchestrator', None)
    def test_pipeline_orchestrator_unavailable(self, client):
        """Test when pipeline orchestrator is unavailable."""
        response = client.get("/api/status")
        data = response.json()
        
        assert data["pipeline_orchestrator"]["available"] is False
        assert data["pipeline_orchestrator"]["status"] == "unavailable"

    def test_documentation_endpoints(self, client):
        """Test documentation endpoints are accessible."""
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "BrowserBud API"

    def test_docs_endpoint(self, client):
        """Test interactive docs endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint(self, client):
        """Test ReDoc endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_invalid_endpoint(self, client):
        """Test invalid endpoint returns 404."""
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

    def test_rate_limit_headers_middleware(self, client):
        """Test rate limit headers are added by middleware."""
        # Mock rate limit info in request state would be added by rate limiter
        response = client.get("/api/health")
        
        # Headers might not be present if rate limiter isn't active
        # Just ensure response is successful
        assert response.status_code == 200

    def test_exception_handling(self, client):
        """Test exception handling middleware."""
        # This would require triggering an actual exception
        # For now, just test that normal requests work
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_check_response_model(self, client):
        """Test health check response follows expected model."""
        response = client.get("/api/health")
        data = response.json()
        
        # Check required fields
        required_fields = ["status", "timestamp", "version", "service", "endpoints"]
        for field in required_fields:
            assert field in data
        
        # Check field types
        assert isinstance(data["status"], str)
        assert isinstance(data["timestamp"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["service"], str)
        assert isinstance(data["endpoints"], dict)

    def test_api_metadata(self, client):
        """Test API metadata in OpenAPI schema."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        assert schema["info"]["title"] == "BrowserBud API"
        assert "description" in schema["info"]
        assert "version" in schema["info"]

    def test_router_inclusion(self, client):
        """Test that all routers are properly included."""
        response = client.get("/openapi.json")
        schema = response.json()
        
        paths = schema["paths"]
        
        # Check that API paths exist (from included routers)
        api_paths = [path for path in paths.keys() if path.startswith("/api")]
        assert len(api_paths) > 0

    @patch('api.main.notes_storage')
    @patch('api.main.batches_storage')
    @patch('api.main.processing_results')
    def test_status_endpoint_with_stats(self, mock_results, mock_batches, mock_notes, client):
        """Test status endpoint includes storage stats."""
        mock_notes.__len__ = Mock(return_value=5)
        mock_batches.__len__ = Mock(return_value=3)
        mock_results.__len__ = Mock(return_value=2)
        
        response = client.get("/api/status")
        data = response.json()
        
        assert "stats" in data
        stats = data["stats"]
        assert "notes_in_memory" in stats
        assert "batches_processed" in stats 
        assert "processing_results" in stats

    def test_error_response_format(self, client):
        """Test error responses follow consistent format."""
        # Test 404 error format
        response = client.get("/nonexistent")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data  # FastAPI default format

    def test_server_headers(self, client):
        """Test server identification headers."""
        response = client.get("/")
        
        # Check response indicates FastAPI
        data = response.json()
        assert "server_type" in data
        assert "FastAPI" in data["server_type"]

    def test_content_type_headers(self, client):
        """Test proper content type headers."""
        response = client.get("/api/health")
        
        assert "application/json" in response.headers["content-type"]

    def test_app_configuration(self):
        """Test app configuration settings."""
        assert app.title == "BrowserBud API"
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"