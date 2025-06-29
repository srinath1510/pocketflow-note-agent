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
        self.config_path = config_path 
        self._version = "1.0.0"
        self.config_data = {}
        
        # Load configuration in order of precedence:
        # 1. Default values
        # 2. Configuration file
        # 3. Environment variables
        self._load_defaults()

        if config_path:
            self._load_from_file(config_path)
        
        self._load_from_environment()
        self._setup_computed_properties()
    
    def _load_defaults(self):
        """Load default configuration values."""
        self.config_data = {
            "version": "1.0.0",
            "pipeline_name": "smart_notes_pipeline", 
            "data_dir": "data",
            "max_notes_per_batch": 100,
            "content_max_length": 50000,
            "log_level": "INFO",
            "log_file": None,
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
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
            # Merge with existing config (file config takes precedence)
            self._deep_merge(self.config_data, file_config)
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
    

    def _load_from_environment(self):
        """Load configuration overrides from environment variables."""
        env_mappings = {
            "SMART_NOTES_LOG_LEVEL": "log_level",
            "SMART_NOTES_LOG_FILE": "log_file",
            "SMART_NOTES_DATA_DIR": "data_dir",
            "SMART_NOTES_MAX_CONCURRENT": "max_concurrent_processes",
            "SMART_NOTES_MAX_NOTES_PER_BATCH": "max_notes_per_batch",
            "SMART_NOTES_CONTENT_MAX_LENGTH": "content_max_length"
        }
        
        for env_var, config_key in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # Type conversion for numeric values
                if config_key in ["max_concurrent_processes", "max_notes_per_batch", "content_max_length"]:
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                
                self.config_data[config_key] = value
    

    def _setup_computed_properties(self):
        """Set up computed configuration properties."""
        base_data_dir = Path(self.config_data["data_dir"])
        
        self.config_data["notes_dir"] = base_data_dir / "notes"
        self.config_data["batches_dir"] = base_data_dir / "batches"
        self.config_data["results_dir"] = base_data_dir / "results"
        self.config_data["temp_dir"] = base_data_dir / "temp"

        for dir_key in ["notes_dir", "batches_dir", "results_dir", "temp_dir"]:
            dir_path = self.config_data[dir_key]
            if isinstance(dir_path, str):
                dir_path = Path(dir_path)
            dir_path.mkdir(parents=True, exist_ok=True)


    def _deep_merge(self, base_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """
        Deep merge two dictionaries.
        
        Args:
            base_dict: Base dictionary to merge into
            update_dict: Dictionary with updates
        """
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    

    def get(self, *path, default=None):
        """
        Get a configuration value
        
        Args:
            key: Configuration key (supports dot notation like 'features.enable_batch_processing')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
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
        Set a configuration value
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        if len(path) == 1 and '.' in path[0]:
            path = path[0].split('.')
    
        current = self.config_data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value

    
    def save_to_file(self, config_path: str):
        """
        Save current configuration to file.
        
        Args:
            config_path: Path where to save configuration
        """
        serializable_config = self._make_serializable(self.config_data.copy())
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_config, f, indent=2, default=str)
    

    def _make_serializable(self, obj: Any) -> Any:
        if isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        else:
            return obj
    
    
    # properties for frequently accessed settings
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.get("log_level", default="INFO")
    
    @property
    def log_file(self) -> Optional[str]:
        """Get log file path."""
        return self.get("log_file")
    
    @property
    def version(self) -> str:
        """Get version."""
        return self.get("version", default="1.0.0")

    @property
    def pipeline_name(self) -> str:
        """Get pipeline name."""
        return self.get("pipeline_name", default="smart_notes_pipeline")

    @property
    def data_dir(self) -> Path:
        """Get data directory."""
        return Path(self.get("data_dir", default="data"))
    
    @property
    def notes_dir(self) -> Path:
        """Get notes directory."""
        return self.config_data["notes_dir"]
    
    @property
    def batches_dir(self) -> Path:
        """Get batches directory."""
        return self.config_data["batches_dir"]
    
    @property
    def results_dir(self) -> Path:
        """Get results directory."""
        return self.config_data["results_dir"]
    
    @property
    def max_notes_per_batch(self) -> int:
        """Get maximum notes per batch."""
        return self.config_data["max_notes_per_batch"]
    
    @property
    def content_max_length(self) -> int:
        """Get maximum content length for capture ingestion."""
        return self.config_data["content_max_length"]
    

    def __str__(self) -> str:
        """String representation of configuration."""
        return f"PipelineConfig(version={self.version}, pipeline_name={self.pipeline_name})"


    def __repr__(self) -> str:
        """Detailed representation of configuration."""
        return f"PipelineConfig(config_path={self.config_path}, version={self.version})"

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