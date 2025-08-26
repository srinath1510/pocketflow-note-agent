#!/usr/bin/env python3
"""
Integration tests for the complete BrowserBud pipeline.
Tests end-to-end functionality with comprehensive mocking.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from tests.fixtures.mock_responses import (
    create_advanced_notion_mock,
    create_pipeline_orchestration_mock,
    create_integration_test_helpers,
    create_fallback_behavior_mocks
)
from tests.fixtures.sample_data import create_sample_learning_session


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""

    @pytest.fixture
    def mock_environment(self):
        """Set up mock environment variables."""
        env_vars = {
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'NOTION_TOKEN': 'test_notion_token',
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_PASSWORD': 'test_password',
            'LLM_PROVIDER': 'anthropic'
        }
        
        with patch.dict('os.environ', env_vars):
            yield env_vars

    @pytest.fixture
    def integration_helpers(self):
        """Get integration test helpers."""
        return create_integration_test_helpers()

    @pytest.fixture
    def fallback_mocks(self):
        """Get fallback behavior mocks."""
        return create_fallback_behavior_mocks()

    def test_complete_pipeline_execution(self, mock_environment, integration_helpers, fallback_mocks):
        """Test complete pipeline execution with all nodes."""
        from main import NoteGenerationPipeline
        
        # Create pipeline with mocked dependencies
        with patch('neo4j.GraphDatabase.driver') as mock_neo4j, \
             patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post:
            
            # Set up mocks
            notion_mock = create_advanced_notion_mock()
            mock_get.side_effect = notion_mock['get'].side_effect
            mock_post.side_effect = notion_mock['post'].side_effect
            
            # Create pipeline
            pipeline = NoteGenerationPipeline()
            
            # Use sample learning session
            test_data = create_sample_learning_session()
            
            # Mock LLM responses
            with patch.object(pipeline.content_analysis_node, 'llm_client', fallback_mocks['llm_client']):
                result = pipeline.run(test_data)
                
                # Verify completion
                assert result is not None
                assert 'session_id' in result
                assert 'pipeline_metadata' in result
                assert result['pipeline_metadata']['status'] == 'completed'

    def test_pipeline_error_recovery(self, mock_environment, fallback_mocks):
        """Test pipeline handles errors gracefully."""
        from main import NoteGenerationPipeline
        
        with patch('neo4j.GraphDatabase.driver') as mock_neo4j:
            pipeline = NoteGenerationPipeline()
            
            # Test with connection failure
            fallback_mocks['notion_api'].set_connection_status('offline')
            
            # Should handle gracefully
            test_data = create_sample_learning_session()
            result = pipeline.run(test_data)
            
            assert result is not None

    def test_sequential_node_execution_logging(self, mock_environment, integration_helpers):
        """Test sequential execution with logging."""
        from nodes.capture_ingestion import CaptureIngestionNode
        
        node = CaptureIngestionNode()
        logger = integration_helpers['sequential_execution']
        
        # Mock shared state
        shared_state = {
            'session_id': 'test_session',
            'raw_input': create_sample_learning_session()
        }
        
        # Execute with logging
        prep_result = node.prep(shared_state)
        logger['log_execution']('capture_ingestion', 'prep', prep_result)
        
        exec_result = node.exec(prep_result)
        logger['log_execution']('capture_ingestion', 'exec', exec_result)
        
        # Verify logging
        log = logger['get_execution_log']()
        assert len(log) == 2
        assert log[0]['node'] == 'capture_ingestion'
        assert log[0]['phase'] == 'prep'
        assert log[0]['success'] is True

    def test_edge_case_handling(self, mock_environment, integration_helpers):
        """Test pipeline handles edge cases."""
        from main import NoteGenerationPipeline
        
        edge_cases = integration_helpers['edge_cases']
        pipeline = NoteGenerationPipeline()
        
        # Test empty input
        with pytest.raises(ValueError):
            pipeline.run(edge_cases['empty_captures'])
        
        # Test minimal input
        result = pipeline.run(edge_cases['minimal_capture'])
        assert result is not None
        
        # Test large content
        result = pipeline.run(edge_cases['large_capture'])
        assert result is not None

    def test_fallback_behavior_coordination(self, mock_environment, fallback_mocks):
        """Test coordination of fallback behaviors across nodes."""
        from nodes.content_analysis import ContentAnalysisNode
        
        node = ContentAnalysisNode()
        
        # Start with LLM available
        llm_client = fallback_mocks['llm_client']
        assert llm_client.is_available() is True
        
        # Toggle availability
        llm_client.toggle_availability(False)
        assert llm_client.is_available() is False
        
        # Node should handle gracefully
        shared_state = {
            'raw_captures': [{'content': 'test', 'metadata': {}}]
        }
        
        with patch.object(node, 'llm_client', llm_client):
            prep_result = node.prep(shared_state)
            assert 'error' not in prep_result


class TestPipelineOrchestration:
    """Test pipeline orchestration patterns."""

    def test_orchestrator_batch_processing(self, mock_environment):
        """Test orchestrator handles batch processing."""
        orchestrator_mock = create_pipeline_orchestration_mock()
        
        # Test batch processing
        test_captures = create_sample_learning_session()
        result = orchestrator_mock.process_captures(test_captures)
        
        assert result['status'] == 'completed'
        assert 'batch_metrics' in result
        assert result['batch_metrics']['api_calls_saved'] > 0

    def test_orchestrator_status_monitoring(self, mock_environment):
        """Test orchestrator status monitoring."""
        orchestrator_mock = create_pipeline_orchestration_mock()
        
        status = orchestrator_mock.get_status()
        
        assert status['status'] == 'operational'
        assert 'active_sessions' in status
        assert 'total_sessions_processed' in status

    def test_orchestrator_error_scenarios(self, mock_environment):
        """Test orchestrator error handling."""
        orchestrator_mock = create_pipeline_orchestration_mock()
        
        # Test different error types
        api_error = orchestrator_mock.create_error_scenario('api_limit')
        assert api_error['status'] == 'failed'
        assert api_error['retry_after'] == 60
        
        db_error = orchestrator_mock.create_error_scenario('database_connection')
        assert db_error['stage'] == 'knowledge_graph'
        assert db_error['partial_results'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])