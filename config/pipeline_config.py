"""
Pipeline Configuration
Contains all configuration settings for the Pipeline
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class PipelineConfig:
    """
    Configuration management
    
    Handles loading configuration from files, environment variables,
    and provides default values for all pipeline settings.
    """

    def __init__ (self, config_path: Optional[str] = None): 
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to configuration JSON file
        """
        self.version = "1.0.0"
        self.config_data = {}
        
        # Load configuration in order of precedence:
        # 1. Default values
        # 2. Configuration file
        # 3. Environment variables
        self._load_defaults()

        if config_path:
            self._load_from_file(config_path)
        
        self._load_from_environment()
    
    def _load_defaults(self):
        """Load default configuration values."""
        self.config_data = {
            # Logging Configuration
            "logging": {
                "log_level": "INFO",
                "log_file": None,  # None means stdout only
                "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            
            # Pipeline Execution Settings
            "pipeline": {
                "max_parallel_nodes": 1,  # Currently sequential execution
                "timeout_seconds": 300,   # 5 minutes
                "retry_attempts": 3,
                "enable_checkpoints": True
            },
            
            # Node 1: Capture Ingestion Settings
            "capture_ingestion": {
                "max_content_length": 1000000,  # 1MB max content
                "html_cleaning": {
                    "remove_scripts": True,
                    "remove_styles": True,
                    "remove_navigation": True,
                    "preserve_links": True,
                    "preserve_formatting": False
                },
                "content_analysis": {
                    "extract_headings": True,
                    "analyze_links": True,
                    "detect_code_blocks": True,
                    "detect_math": True,
                    "count_citations": True
                },
                "validation": {
                    "required_fields": ["url", "content", "timestamp"],
                    "validate_urls": True,
                    "min_content_length": 10
                }
            },
            
            # Content Classification Settings
            "content_classification": {
                "patterns": {
                    "research_paper": [
                        r"abstract\s*:?\s*\n",
                        r"references\s*:?\s*\n",
                        r"doi\s*:?\s*10\.",
                        r"arxiv\.org",
                        r"pubmed\.ncbi\.nlm\.nih\.gov"
                    ],
                    "documentation": [
                        r"api\s+reference",
                        r"getting\s+started",
                        r"installation\s+guide",
                        r"docs?\.",
                        r"github\.io"
                    ],
                    "blog_post": [
                        r"posted\s+on",
                        r"by\s+.+\s+on",
                        r"comments?\s*\(",
                        r"share\s+this",
                        r"medium\.com",
                        r"dev\.to"
                    ],
                    "news_article": [
                        r"breaking\s+news",
                        r"reuters\.com",
                        r"cnn\.com",
                        r"bbc\.co\.uk",
                        r"published\s+\d+\s+hours?\s+ago"
                    ]
                }
            }
        }
    

    def _load_from_file(self, config_path: str):
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                
                # Merge with existing config (file config takes precedence)
                self._deep_merge(self.config_data, file_config)
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
    

    def _load_from_environment(self):
        """Load configuration overrides from environment variables."""
        env_mapping = {
            "PIPELINE_LOG_LEVEL": ["logging", "log_level"],
            "PIPELINE_LOG_FILE": ["logging", "log_file"],
            "PIPELINE_TIMEOUT": ["pipeline", "timeout_seconds"],
            "PIPELINE_RETRY_ATTEMPTS": ["pipeline", "retry_attempts"],
            "CAPTURE_MAX_CONTENT_LENGTH": ["capture_ingestion", "max_content_length"],
            "LLM_PROVIDER": ["content_analysis", "llm_provider"],
            "LLM_MODEL": ["content_analysis", "model_name"],
            "OUTPUT_VAULT_PATH": ["output", "vault_path"]
        }
        
        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Try to convert to appropriate type
                try:
                    # Try integer conversion
                    if value.isdigit():
                        value = int(value)
                    # Try boolean conversion
                    elif value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                except ValueError:
                    pass  # Keep as string
                
                # Set the configuration value
                self._set_nested_value(self.config_data, config_path, value)
    

    def _deep_merge(self, base_dict: Dict[str, Any], override_dict: Dict[str, Any]):
        """
        Deep merge two dictionaries.
        
        Args:
            base_dict: Base dictionary to merge into
            override_dict: Dictionary with override values
        """
        for key, value in override_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    

    def _set_nested_value(self, config_dict: Dict[str, Any], path: list, value: Any):
        """
        Set a nested configuration value using a path list.
        
        Args:
            config_dict: Configuration dictionary
            path: List of keys representing the path
            value: Value to set
        """
        current = config_dict
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
    

    def get(self, *path, default=None):
        """
        Get a configuration value using dot notation or path components.
        
        Args:
            *path: Path components (e.g., 'logging', 'log_level' or 'logging.log_level')
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        # Handle dot notation in first argument
        if len(path) == 1 and '.' in path[0]:
            path = path[0].split('.')
        
        current = self.config_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current


    def set(self, *path, value):
        """
        Set a configuration value using path components.
        
        Args:
            *path: Path components
            value: Value to set
        """
        # Handle dot notation in first argument
        if len(path) == 1 and '.' in path[0]:
            path = path[0].split('.')
        
        self._set_nested_value(self.config_data, list(path), value)
    

    def to_dict(self) -> Dict[str, Any]:
        """Return the complete configuration as a dictionary."""
        return self.config_data.copy()
    

    def save(self, file_path: str):
        """
        Save current configuration to a JSON file.
        
        Args:
            file_path: Path where to save the configuration
        """
        config_file = Path(file_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=2)
    
    # properties for frequently accessed settings
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.get("logging", "log_level")
    
    @property
    def log_file(self) -> Optional[str]:
        """Get log file path."""
        return self.get("logging", "log_file")
    
    @property
    def pipeline_timeout(self) -> int:
        """Get pipeline timeout in seconds."""
        return self.get("pipeline", "timeout_seconds")
    
    @property
    def max_content_length(self) -> int:
        """Get maximum content length for capture ingestion."""
        return self.get("capture_ingestion", "max_content_length")
    
    @property
    def vault_path(self) -> str:
        """Get output vault path."""
        return self.get("output", "vault_path")


# Example configuration file that users can customize
EXAMPLE_CONFIG = {
    "logging": {
        "log_level": "DEBUG",
        "log_file": "logs/pipeline.log"
    },
    "pipeline": {
        "timeout_seconds": 600,
        "retry_attempts": 2
    },
    "capture_ingestion": {
        "max_content_length": 2000000,
        "validation": {
            "min_content_length": 50
        }
    },
    "content_analysis": {
        "llm_provider": "openai",
        "model_name": "gpt-4-turbo",
        "temperature": 0.2
    },
    "output": {
        "vault_path": "./my_research_vault",
        "export_format": "obsidian"
    }
}


def create_example_config(file_path: str = "config/example_config.json"):
    """
    Create an example configuration file.
    
    Args:
        file_path: Where to save the example configuration
    """
    config_file = Path(file_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(EXAMPLE_CONFIG, f, indent=2)
    
    print(f"Example configuration created at: {config_file}")


if __name__ == "__main__":
    # Create example configuration if run directly
    create_example_config()