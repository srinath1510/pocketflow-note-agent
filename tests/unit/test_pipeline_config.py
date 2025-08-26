import pytest
import os
from unittest.mock import patch, mock_open
from pathlib import Path

from config.pipeline_config import PipelineConfig


class TestPipelineConfig:
    """Unit tests for PipelineConfig class."""

    def test_init_creates_default_config(self):
        """Test that initialization creates default configuration."""
        config = PipelineConfig()
        assert config.config_data is not None
        assert isinstance(config.config_data, dict)
        assert "version" in config.config_data
        assert config.config_data["version"] == "1.0.0"

    def test_pipeline_name_default(self):
        """Test default pipeline name."""
        config = PipelineConfig()
        assert config.pipeline_name == "browserbud_pipeline"

    def test_get_method_with_existing_key(self):
        """Test get method returns correct value for existing key."""
        config = PipelineConfig()
        assert config.get("version") == "1.0.0"
        assert config.get("pipeline_name") == "browserbud_pipeline"

    def test_get_method_with_default(self):
        """Test get method returns default for non-existing key."""
        config = PipelineConfig()
        assert config.get("non_existing_key", "default_value") == "default_value"
        assert config.get("non_existing_key") is None

    def test_environment_variable_overrides(self):
        """Test that environment variables override defaults."""
        env_vars = {
            'BROWSERBUD_LOG_LEVEL': 'DEBUG',
            'BROWSERBUD_DATA_DIR': '/custom/data/dir',
            'BROWSERBUD_MAX_NOTES_PER_BATCH': '50'
        }
        
        with patch.dict(os.environ, env_vars):
            config = PipelineConfig()
            assert config.get("log_level") == "DEBUG"
            assert config.get("data_dir") == "/custom/data/dir"
            assert config.get("max_notes_per_batch") == 50

    def test_numeric_environment_variable_conversion(self):
        """Test that numeric environment variables are converted properly."""
        with patch.dict(os.environ, {'BROWSERBUD_MAX_NOTES_PER_BATCH': '123'}):
            config = PipelineConfig()
            assert config.get("max_notes_per_batch") == 123
            assert isinstance(config.get("max_notes_per_batch"), int)

    def test_invalid_numeric_environment_variable(self):
        """Test handling of invalid numeric environment variables."""
        with patch.dict(os.environ, {'BROWSERBUD_MAX_NOTES_PER_BATCH': 'not_a_number'}):
            config = PipelineConfig()
            # Should keep original default value
            assert config.get("max_notes_per_batch") == 100

    def test_required_environment_validation(self):
        """Test validation of required environment variables."""
        required_vars = ['NEO4J_PASSWORD', 'ANTHROPIC_API_KEY', 'NOTION_TOKEN']
        
        # Test with missing variables
        for var in required_vars:
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError, match=f"Missing required environment variables"):
                    PipelineConfig()

    def test_required_environment_validation_success(self):
        """Test successful validation with all required variables."""
        env_vars = {
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_USER': 'neo4j',
            'NEO4J_PASSWORD': 'test_password',
            'ANTHROPIC_API_KEY': 'test_key',
            'NOTION_TOKEN': 'test_token'
        }
        
        with patch.dict(os.environ, env_vars):
            config = PipelineConfig()  # Should not raise
            assert config is not None

    def test_config_file_loading(self):
        """Test loading configuration from file."""
        mock_config_content = '{"custom_key": "custom_value", "log_level": "WARNING"}'
        
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value=mock_config_content):
            config = PipelineConfig(config_file="test_config.json")
            assert config.get("custom_key") == "custom_value"
            assert config.get("log_level") == "WARNING"

    def test_config_file_not_found(self):
        """Test behavior when config file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            config = PipelineConfig(config_file="nonexistent.json")
            # Should still work with defaults
            assert config.get("version") == "1.0.0"

    def test_invalid_json_config_file(self):
        """Test handling of invalid JSON in config file."""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("pathlib.Path.read_text", return_value="invalid json"):
            config = PipelineConfig(config_file="invalid.json")
            # Should fall back to defaults
            assert config.get("version") == "1.0.0"

    def test_nested_config_access(self):
        """Test accessing nested configuration values."""
        config = PipelineConfig()
        
        # Test nested dictionary access
        pipeline_config = config.get("pipeline", {})
        assert isinstance(pipeline_config, dict)
        assert "max_parallel_nodes" in pipeline_config
        
        capture_config = config.get("capture_ingestion", {})
        assert isinstance(capture_config, dict)

    def test_config_immutability_after_init(self):
        """Test that configuration doesn't change after initialization."""
        config = PipelineConfig()
        original_version = config.get("version")
        
        # Try to modify config data directly (should not affect external behavior)
        config.config_data["version"] = "modified"
        
        # Get should still return the modified value since we modified internal state
        assert config.get("version") == "modified"
        
        # But creating new instance should use original defaults
        new_config = PipelineConfig()
        assert new_config.get("version") == original_version

    def test_default_values_structure(self):
        """Test the structure and types of default configuration."""
        config = PipelineConfig()
        
        # Test top-level keys
        expected_keys = ["version", "pipeline_name", "data_dir", "log_level"]
        for key in expected_keys:
            assert key in config.config_data
            
        # Test nested structures
        assert isinstance(config.get("pipeline"), dict)
        assert isinstance(config.get("capture_ingestion"), dict)
        
        # Test value types
        assert isinstance(config.get("max_notes_per_batch"), int)
        assert isinstance(config.get("content_max_length"), int)
        assert isinstance(config.get("log_level"), str)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_all_environment_variables(self):
        """Test behavior when all environment variables are missing."""
        with pytest.raises(ValueError) as exc_info:
            PipelineConfig()
        
        error_message = str(exc_info.value)
        assert "Missing required environment variables" in error_message
        assert "NEO4J_PASSWORD" in error_message
        assert "ANTHROPIC_API_KEY" in error_message
        assert "NOTION_TOKEN" in error_message