"""
Main Pipeline Entry Point
Orchestrates the AI Note Generation Pipeline for Web Research → Obsidian Notes
"""
import json
import logging
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv()

from pocketflow import Flow
from nodes.capture_ingestion import CaptureIngestionNode
from nodes.content_analysis import ContentAnalysisNode
from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
from nodes.notion_note_generation import NotionNoteGenerationNode
from config.pipeline_config import PipelineConfig

from nodes.knowledge_graph import KnowledgeGraphNode


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

        self.capture_ingestion_node = CaptureIngestionNode()
        self.content_analysis_node = ContentAnalysisNode()
        self.knowledge_graph_node = KnowledgeGraphNode()
        self.historical_knowledge_node = HistoricalKnowledgeRetrievalNode()
        self.notion_generation_node = NotionNoteGenerationNode() 

        self._build_pipeline()
        self.logger.info("Pipeline initialized with 5 connected nodes including Notion Note Generation")

    def _build_pipeline(self):
        """Build the complete pipeline flow"""
        # Linear flow: each node passes to the next
        self.capture_ingestion_node >> self.content_analysis_node
        self.content_analysis_node >> self.knowledge_graph_node
        self.knowledge_graph_node >> self.historical_knowledge_node
        self.historical_knowledge_node >> self.notion_generation_node
        
        # Create the main flow starting from capture ingestion
        self.flow = Flow(self.capture_ingestion_node)
        self.flow >> self.content_analysis_node
        self.content_analysis_node >> self.knowledge_graph_node
        self.knowledge_graph_node >> self.historical_knowledge_node
        self.historical_knowledge_node >> self.notion_generation_node

        
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
        
        
    def run(self, input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
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
                "pipeline_version": "1.1.0"
            }
        }
        
        try:
            # Execute pipeline
            self.flow.run(shared_state)
            
            # Add completion metadata
            shared_state["pipeline_metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
            shared_state["pipeline_metadata"]["status"] = "completed"
            shared_state["pipeline_stage"] = "completed"
            
            self.logger.info(f"Pipeline execution completed successfully - Session ID: {session_id}")

            raw_captures = shared_state.get('raw_captures', [])
            extracted_concepts = shared_state.get('extracted_concepts', {})
            knowledge_graph = shared_state.get('knowledge_graph', {})
            historical_connections = shared_state.get('historical_connections', {})
            notion_generation = shared_state.get('notion_generation', {})


            self.logger.info(f"Processed {len(raw_captures)} captures")
            self.logger.info(f"Extracted {len(extracted_concepts.get('key_concepts', []))} concepts")
            self.logger.info(f"Created {knowledge_graph.get('nodes_created', {}).get('concepts', 0)} knowledge graph nodes")
            self.logger.info(f"Found {historical_connections.get('total_connections_found', 0)} historical connections")

            if notion_generation:
                self.logger.info(f"Generated Notion page: {notion_generation.get('session_page_url', 'Unknown')}")


            return shared_state
            
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
            if node_name == "capture_ingestion":
                node = self.capture_ingestion_node
            elif node_name == "content_analysis":
                self.capture_ingestion_node.run(shared_state)
                node = self.content_analysis_node
            elif node_name == "knowledge_graph":
                self.capture_ingestion_node.run(shared_state)
                self.content_analysis_node.run(shared_state)
                node = self.knowledge_graph_node
            elif node_name == "historical_knowledge":
                # Run all prerequisite nodes
                self.capture_ingestion_node.run(shared_state)
                self.content_analysis_node.run(shared_state)
                self.knowledge_graph_node.run(shared_state)
                node = self.historical_knowledge_node
            elif node_name == "notion_generation":
                # Run all prerequisite nodes
                self.capture_ingestion_node.run(shared_state)
                self.content_analysis_node.run(shared_state)
                self.knowledge_graph_node.run(shared_state)
                self.historical_knowledge_node.run(shared_state)
                node = self.notion_generation_node
            else:
                raise ValueError(f"Node '{node_name}' not found in pipeline")
            
            node.run(shared_state)
            
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
            
            # Capture ingestion results
            if "raw_captures" in result:
                captures = result["raw_captures"]
                print(f"\n📥 CAPTURE INGESTION:")
                print(f"   Processed Captures: {len(captures)}")
                
                if captures:
                    print(f"   Sample Captures:")
                    for i, capture in enumerate(captures[:2]):  # Show first 2
                        print(f"     {i+1}. {capture['metadata']['page_title'][:40]}...")
                        print(f"        URL: {capture['url']}")
                        print(f"        Category: {capture['metadata']['content_category']}")
            
            # Content analysis results
            if "extracted_concepts" in result:
                concepts = result["extracted_concepts"]
                print(f"\n🧠 CONTENT ANALYSIS:")
                print(f"   Learning Concepts: {len(concepts.get('learning_concepts', []))}")
                print(f"   Key Terms: {len(concepts.get('key_terms', {}))}")
                print(f"   Entities: {len(concepts.get('entities', {}))}")
                print(f"   Session Theme: {concepts.get('session_theme', 'unknown')}")
                
                if concepts.get('learning_concepts'):
                    print(f"   Top Concepts: {', '.join(concepts['learning_concepts'][:3])}")
            
            # Knowledge graph results
            if "knowledge_graph" in result:
                kg = result["knowledge_graph"]
                print(f"\n🕸️ KNOWLEDGE GRAPH:")
                nodes_created = kg.get('nodes_created', {})
                print(f"   Concepts: {nodes_created.get('concepts', 0)} nodes")
                print(f"   Entities: {nodes_created.get('entities', 0)} nodes") 
                print(f"   Topics: {nodes_created.get('topics', 0)} nodes")
                print(f"   Resources: {nodes_created.get('resources', 0)} nodes")
                print(f"   Relationships: {kg.get('relationships_created', 0)}")
                
                metrics = kg.get('metrics', {})
                print(f"   Graph Density: {metrics.get('graph_density', 0):.3f}")
            
            # Historical knowledge results
            if "historical_connections" in result:
                hist = result.get('historical_connections', {})
                gaps = result.get('knowledge_gaps', [])
                reinforcement = result.get('reinforcement_opportunities', [])
                recommendations = result.get('learning_recommendations', [])
                
                print(f"\n🔗 HISTORICAL KNOWLEDGE ANALYSIS:")
                print(f"   Total Connections Found: {hist.get('total_connections_found', 0)}")
                print(f"   Knowledge Gaps Identified: {len(gaps)}")
                print(f"   Reinforcement Opportunities: {len(reinforcement)}")
                print(f"   Learning Recommendations: {len(recommendations)}")
                
                # Show high-priority recommendations
                high_priority = [r for r in recommendations if r.get('priority') == 'high']
                if high_priority:
                    print(f"\n   🚨 High Priority Recommendations:")
                    for rec in high_priority[:2]:
                        print(f"     • {rec.get('action', 'No action')}")
                        print(f"       Reason: {rec.get('reason', 'No reason')}")
                
                # Show knowledge gaps
                if gaps:
                    print(f"\n   📚 Knowledge Gaps to Address:")
                    for gap in gaps[:2]:
                        print(f"     • Missing: {gap.get('missing_concept', 'Unknown')}")
                        print(f"       Priority: {gap.get('priority', 'medium')}")
            
            # Notion note generation results
            if "notion_generation" in result:
                notion = result["notion_generation"]
                creation_summary = notion.get('creation_summary', {})
                
                print(f"\n📄 NOTION NOTE GENERATION:")
                print(f"   Session Page Created: {'✅' if creation_summary.get('session_created') else '❌'}")
                print(f"   Concepts Created: {creation_summary.get('concepts_created', 0)}")
                print(f"   Sources Created: {creation_summary.get('sources_created', 0)}")
                print(f"   Total Pages: {creation_summary.get('total_pages', 0)}")
                
                session_url = notion.get('session_page_url')
                if session_url:
                    print(f"\n   🔗 Notion Session Page:")
                    print(f"      {session_url}")
                    print(f"\n   💡 Open this URL to see your beautifully formatted learning session!")
                else:
                    print(f"\n   ⚠️ Session page URL not available")
            
            print("\n" + "="*70)
            print("Pipeline execution complete! 🎉")
            
            # Show next steps
            notion_gen = result.get('notion_generation')
            if notion_gen and notion_gen.get('session_page_url'):
                print("\n🎯 NEXT STEPS:")
                print("1. Open your Notion session page to see the rich, formatted notes")
                print("2. Explore the concept and source databases")
                print("3. Review knowledge gaps and recommendations")
                print("4. Use the todo items to guide your next learning steps")
                print("\nYour AI-powered second brain is now living in Notion! 🧠✨")
            else:
                print("\nYour learning session has been analyzed and processed through all pipeline stages.")
                print("Set up Notion integration to get beautiful, structured notes automatically!")
    
    except Exception as e:
        print(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()