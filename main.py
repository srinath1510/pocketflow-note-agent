"""
Main Pipeline Entry Point
Orchestrates the AI Note Generation Pipeline for Web Research → Obsidian Notes
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from pocketflow import PipelineRunner
from nodes.capture_ingestion import CaptureIngestionNode
from config.pipeline_config import PipelineConfig


class NoteGenerationPipeline:
    """
    Main pipeline class for orchestrating the AI Note Generation Pipeline.
    
    Processes raw browser captures through multiple nodes to generate
    structured Obsidian notes with comprehensive cross-references.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the pipeline.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = PipelineConfig(config_path)
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        self.runner = PipelineRunner()
        
        # Register nodes in execution order
        self._register_nodes()
        
    def setup_logging(self):
        """Configure logging based on pipeline configuration."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.config.log_file) if self.config.log_file else logging.NullHandler()
            ]
        )
        
    def _register_nodes(self):
        """Register all pipeline nodes in execution order."""
        self.logger.info("Registering pipeline nodes")
        
        # Node 1: Capture Ingestion
        self.runner.add_node("capture_ingestion", CaptureIngestionNode())
        
        # TODO: Add additional nodes as they are implemented
        # Node 2: Content Analysis & Concept Extraction
        # self.runner.add_node("content_analysis", ContentAnalysisNode())
        
        # Node 3: Cross-Capture Relationship Mapping
        # self.runner.add_node("relationship_mapping", RelationshipMappingNode())
        
        # Node 4: Note Structure Planning
        # self.runner.add_node("structure_planning", StructurePlanningNode())
        
        # Node 5: Content Generation & Template Application
        # self.runner.add_node("content_generation", ContentGenerationNode())
        
        # Node 6: Link Weaving & Cross-Reference Generation
        # self.runner.add_node("link_weaving", LinkWeavingNode())
        
        # Node 7: Quality Assurance & Validation
        # self.runner.add_node("quality_assurance", QualityAssuranceNode())
        
        # Node 8: Vault Assembly & Export
        # self.runner.add_node("vault_assembly", VaultAssemblyNode())
        
        self.logger.info(f"Registered {len(self.runner.nodes)} nodes")
        
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the complete pipeline.
        
        Args:
            input_data: Raw capture data from browser extension
            
        Returns:
            Processed shared state with generated notes
        """
        session_id = f"session_{int(datetime.now(timezone.utc).timestamp())}"
        self.logger.info(f"Starting pipeline execution - Session ID: {session_id}")
        
        # Initialize shared state
        shared_state = {
            "session_id": session_id,
            "pipeline_stage": "initialization",
            "raw_input": input_data,
            "pipeline_metadata": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "config_version": self.config.version,
                "pipeline_version": "1.0.0"
            }
        }
        
        try:
            # Execute pipeline
            result = self.runner.run(shared_state)
            
            # Add completion metadata
            result["pipeline_metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
            result["pipeline_metadata"]["status"] = "completed"
            result["pipeline_stage"] = "completed"
            
            self.logger.info(f"Pipeline execution completed successfully - Session ID: {session_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)
            
            # Add error metadata
            shared_state["pipeline_metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
            shared_state["pipeline_metadata"]["status"] = "failed"
            shared_state["pipeline_metadata"]["error"] = str(e)
            shared_state["pipeline_stage"] = "failed"
            
            raise
    
    def run_single_node(self, node_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single node for testing purposes.
        
        Args:
            node_name: Name of the node to execute
            input_data: Input data for the node
            
        Returns:
            Processed shared state
        """
        self.logger.info(f"Running single node: {node_name}")
        
        # Initialize shared state
        shared_state = {
            "session_id": f"test_{int(datetime.now(timezone.utc).timestamp())}",
            "pipeline_stage": f"testing_{node_name}",
            "raw_input": input_data,
            "pipeline_metadata": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "test_mode": True,
                "target_node": node_name
            }
        }
        
        try:
            # Get the specific node
            if node_name not in self.runner.nodes:
                raise ValueError(f"Node '{node_name}' not found in pipeline")
            
            node = self.runner.nodes[node_name]
            
            # Execute node phases
            shared_state = node.prep(shared_state)
            shared_state = node.execCore(shared_state)
            shared_state = node.post(shared_state)
            
            # Add completion metadata
            shared_state["pipeline_metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
            shared_state["pipeline_metadata"]["status"] = "completed"
            
            self.logger.info(f"Single node execution completed: {node_name}")
            return shared_state
            
        except Exception as e:
            self.logger.error(f"Single node execution failed: {str(e)}", exc_info=True)
            raise


def load_sample_data(file_path: str) -> Dict[str, Any]:
    """
    Load sample capture data from JSON file.
    
    Args:
        file_path: Path to sample data file
        
    Returns:
        Sample capture data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return minimal sample data if file not found
        return {
            "url": "https://example.com/sample-article",
            "content": "<html><head><title>Sample Article</title></head><body><h1>Sample Article</h1><p>This is a sample article for testing the pipeline.</p></body></html>",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "selected_text": "sample article",
            "highlights": ["This is a sample article"],
            "dwell_time": 30000,
            "scroll_depth": 0.5,
            "viewport_size": "1440x900",
            "user_agent": "Mozilla/5.0 (Test Browser)",
            "trigger": "test",
            "intent": "testing"
        }


def main():
    """Main entry point for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Note Generation Pipeline")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--input", help="Path to input JSON file with capture data")
    parser.add_argument("--output", help="Path to output JSON file for results")
    parser.add_argument("--node", help="Run single node only (for testing)")
    parser.add_argument("--sample", action="store_true", help="Use built-in sample data")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline
        pipeline = NoteGenerationPipeline(args.config)
        
        # Override log level if verbose requested
        if args.verbose:
            pipeline.config.log_level = "DEBUG"
            pipeline.setup_logging()
        
        # Determine input data
        if args.sample:
            input_data = load_sample_data("")  # Use built-in sample
        elif args.input:
            input_data = load_sample_data(args.input)
        else:
            print("Error: Must specify --input file or --sample flag")
            sys.exit(1)
        
        # Execute pipeline or single node
        if args.node:
            result = pipeline.run_single_node(args.node, input_data)
        else:
            result = pipeline.run(input_data)
        
        # Output results
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"Results saved to: {output_path}")
        else:
            # Print summary to console
            print("\n" + "="*50)
            print("PIPELINE EXECUTION SUMMARY")
            print("="*50)
            
            metadata = result.get("pipeline_metadata", {})
            print(f"Session ID: {result.get('session_id', 'Unknown')}")
            print(f"Status: {metadata.get('status', 'Unknown')}")
            print(f"Start Time: {metadata.get('start_time', 'Unknown')}")
            print(f"End Time: {metadata.get('end_time', 'Unknown')}")
            
            if "raw_captures" in result:
                captures = result["raw_captures"]
                print(f"Processed Captures: {len(captures)}")
                
                if captures:
                    print("\nCapture Details:")
                    for i, capture in enumerate(captures[:3]):  # Show first 3
                        print(f"  {i+1}. {capture['metadata']['page_title'][:50]}...")
                        print(f"     URL: {capture['url']}")
                        print(f"     Content Length: {len(capture['content'])} chars")
                        print(f"     Category: {capture['metadata']['content_category']}")
                    
                    if len(captures) > 3:
                        print(f"  ... and {len(captures) - 3} more")
            
            print("="*50)
    
    except Exception as e:
        print(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()