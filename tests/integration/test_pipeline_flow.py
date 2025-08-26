import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from main import NoteGenerationPipeline
from tests.fixtures.sample_data import SAMPLE_MINIMAL_CAPTURES, SAMPLE_EXTRACTED_CONCEPTS


@pytest.mark.integration
class TestPipelineFlow:
    """Integration tests for complete pipeline flow."""

    @pytest.fixture
    def pipeline(self, test_config):
        """Create pipeline instance with test configuration."""
        with patch('main.PipelineConfig', return_value=test_config):
            return NoteGenerationPipeline()

    @pytest.fixture
    def mock_external_services(self, mock_neo4j_driver, mock_anthropic_client, mock_notion_client):
        """Mock all external services."""
        with patch('nodes.knowledge_graph.GraphDatabase.driver', return_value=mock_neo4j_driver), \
             patch('nodes.content_analysis.get_llm_client', return_value=mock_anthropic_client), \
             patch('nodes.notion_note_generation.NotionClient', return_value=mock_notion_client):
            yield

    def test_complete_pipeline_flow(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test complete pipeline from input to output."""
        # Mock LLM response for content analysis
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
        
        # Verify pipeline completion
        assert "session_id" in result
        assert "user_id" in result
        assert result["user_id"] == "test_user_001"
        
        # Verify all stages completed
        assert "raw_captures" in result
        assert "extracted_concepts" in result
        assert "knowledge_graph" in result
        assert "notion_generation" in result
        
        # Verify pipeline metadata
        metadata = result["pipeline_metadata"]
        assert metadata["status"] == "completed"
        assert metadata["stages_completed"] > 0

    def test_pipeline_stage_sequence(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test that pipeline stages execute in correct sequence."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        with patch.object(pipeline, '_execute_stage') as mock_execute:
            # Mock each stage to return expected data
            mock_execute.side_effect = [
                ({"raw_captures": []}, "default"),
                ({"extracted_concepts": {}}, "default"), 
                ({"knowledge_graph": {}}, "default"),
                ({"historical_connections": {}}, "default"),
                ({"notion_generation": {}}, "default")
            ]
            
            pipeline.run(SAMPLE_MINIMAL_CAPTURES)
            
            # Verify stages called in order
            expected_stages = [
                "capture_ingestion",
                "content_analysis", 
                "knowledge_graph",
                "historical_knowledge",
                "notion_generation"
            ]
            
            actual_stages = [call[0][0] for call in mock_execute.call_args_list]
            assert actual_stages == expected_stages

    def test_pipeline_error_handling(self, pipeline, mock_external_services):
        """Test pipeline error handling at different stages."""
        # Test capture ingestion error
        with patch.object(pipeline, '_execute_stage') as mock_execute:
            mock_execute.return_value = ({"error": "Capture ingestion failed"}, "error")
            
            result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
            
            assert result["pipeline_metadata"]["status"] == "failed"
            assert "error" in result

    def test_pipeline_partial_completion(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test pipeline behavior when some stages fail."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        # Mock stages: first two succeed, third fails
        with patch.object(pipeline, '_execute_stage') as mock_execute:
            mock_execute.side_effect = [
                ({"raw_captures": []}, "default"),
                ({"extracted_concepts": SAMPLE_EXTRACTED_CONCEPTS}, "default"),
                ({"error": "Knowledge graph failed"}, "error"),
            ]
            
            result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
            
            # Should have partial results
            assert "raw_captures" in result
            assert "extracted_concepts" in result
            assert result["pipeline_metadata"]["status"] == "failed"

    def test_data_flow_between_stages(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test that data flows correctly between stages."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
        
        # Verify data dependencies
        assert len(result["raw_captures"]) > 0
        
        # Content analysis should use raw captures
        concepts = result["extracted_concepts"]
        assert len(concepts["learning_concepts"]) > 0
        
        # Knowledge graph should use extracted concepts
        kg = result["knowledge_graph"]
        assert "nodes_created" in kg
        
        # Notion generation should use all previous stages
        notion = result["notion_generation"]
        assert "creation_summary" in notion

    def test_batch_processing_integration(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test batch processing across multiple stages."""
        # Provide multiple captures for batch processing
        large_input = SAMPLE_MINIMAL_CAPTURES * 3
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        result = pipeline.run(large_input)
        
        assert len(result["raw_captures"]) == len(large_input)
        assert "batch_metrics" in result
        
        # Should have batch optimization metrics
        metrics = result["batch_metrics"]
        assert "api_calls_made" in metrics
        assert "batches_processed" in metrics

    def test_session_consistency(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test session ID consistency across stages."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
        
        session_id = result["session_id"]
        
        # Verify session ID is consistent across all stages
        for capture in result["raw_captures"]:
            assert capture["session_id"] == session_id
            
        assert result["extracted_concepts"]["session_id"] == session_id
        assert result["knowledge_graph"]["session_id"] == session_id

    def test_user_context_preservation(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test that user context is preserved throughout pipeline."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
        
        user_id = result["user_id"]
        
        # Verify user ID is consistent
        for capture in result["raw_captures"]:
            assert capture["user_id"] == user_id

    def test_pipeline_timing_metrics(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test pipeline timing and performance metrics."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
        
        metadata = result["pipeline_metadata"]
        assert "start_time" in metadata
        assert "end_time" in metadata
        
        # Verify timestamps are valid
        assert metadata["start_time"] <= metadata["end_time"]

    @pytest.mark.slow
    def test_large_dataset_processing(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test pipeline with large dataset."""
        # Create large dataset
        large_dataset = []
        for i in range(20):
            capture = {**SAMPLE_MINIMAL_CAPTURES[0]}
            capture["content"] = f"Content variation {i}: " + capture["content"]
            capture["title"] = f"Title {i}"
            large_dataset.append(capture)
        
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        result = pipeline.run(large_dataset)
        
        assert len(result["raw_captures"]) == 20
        assert "batch_metrics" in result
        
        # Should optimize batch processing for large datasets
        metrics = result["batch_metrics"]
        assert metrics["batches_processed"] > 1
        assert metrics["api_calls_made"] < len(large_dataset)  # Due to batching

    def test_pipeline_state_isolation(self, pipeline, mock_external_services, mock_anthropic_client):
        """Test that multiple pipeline runs don't interfere."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        # Run pipeline twice with different inputs
        result1 = pipeline.run(SAMPLE_MINIMAL_CAPTURES[:1])
        result2 = pipeline.run(SAMPLE_MINIMAL_CAPTURES[1:])
        
        # Sessions should be different
        assert result1["session_id"] != result2["session_id"]
        
        # Results should be independent
        assert len(result1["raw_captures"]) == 1
        assert len(result2["raw_captures"]) == 1

    def test_pipeline_configuration_effects(self, mock_external_services, mock_anthropic_client):
        """Test that pipeline configuration affects behavior."""
        mock_anthropic_client.chat_completion.return_value = json.dumps(SAMPLE_EXTRACTED_CONCEPTS)
        
        # Test with different batch sizes
        with patch('main.PipelineConfig') as mock_config:
            config = Mock()
            config.get.side_effect = lambda key, default=None: {
                "max_notes_per_batch": 2,
                "content_max_length": 1000
            }.get(key, default)
            mock_config.return_value = config
            
            pipeline = NoteGenerationPipeline()
            result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
            
            # Configuration should affect processing
            assert "batch_metrics" in result

    def test_error_recovery_mechanisms(self, pipeline, mock_external_services):
        """Test pipeline error recovery and fallbacks."""
        # Mock intermittent failures
        with patch.object(pipeline, '_execute_stage') as mock_execute:
            # First call fails, second succeeds
            mock_execute.side_effect = [
                ({"error": "Temporary failure"}, "retry"),
                ({"raw_captures": []}, "default")
            ]
            
            # This test would require retry logic implementation
            # For now, just verify error handling
            result = pipeline.run(SAMPLE_MINIMAL_CAPTURES)
            assert "pipeline_metadata" in result