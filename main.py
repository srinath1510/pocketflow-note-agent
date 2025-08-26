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
    Main pipeline class for orchestrating the BrowserBud Pipeline.
    
    Processes raw browser captures through multiple nodes to generate
    structured Notion notes with comprehensive cross-references.
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
        
        
    def run(self, input_captures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute the complete pipeline.
        
        Args:
            input_captures: List of capture dictionaries in minimal format:
                [
                    {
                        "content": "string",  # Required
                        "user_id": "string",  # Required
                        "source_url": "string",  # Optional
                        "title": "string",  # Optional
                        "timestamp": "ISO string",  # Optional
                        "intent": "learn|research|reference|archive",  # Optional
                        "user_note": "string"  # Optional
                    }
                ]
            
        Returns:
            Processed shared state with results
        """
        if not input_captures:
            raise ValueError("No input captures provided")

        # Generate session ID
        user_id = input_captures[0].get('user_id', 'unknown')
        session_id = f"{user_id}_session_{int(datetime.now(timezone.utc).timestamp())}"
        
        self.logger.info(f"🎯 Starting pipeline execution")
        self.logger.info(f"   Session ID: {session_id}")
        self.logger.info(f"   User ID: {user_id}")
        self.logger.info(f"   Captures: {len(input_captures)}")
        
        # Initialize shared state
        shared_state = {
            "session_id": session_id,
            "user_id": user_id,
            "pipeline_stage": "initialization",
            "raw_input": input_captures,  # Store original minimal input
            "pipeline_metadata": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "input_format": "minimal_capture",
                "pipeline_version": "1.1.0-modular",
                "captures_count": len(input_captures)
            }
        }
        try:
            self.flow.run(shared_state)
            shared_state["pipeline_metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
            shared_state["pipeline_metadata"]["status"] = "completed"
            shared_state["pipeline_stage"] = "completed"

            batch_metrics = shared_state.get('batch_metrics')
            if batch_metrics:
                self.logger.info(f"✅ Batch metrics preserved in final result: {batch_metrics.get('api_calls_saved', 0)} calls saved")
            else:
                self.logger.warning("⚠️  No batch metrics found in final shared_state")
                # Check pipeline_metadata as backup
                batch_metrics = shared_state.get('pipeline_metadata', {}).get('batch_optimization_metrics')
                if batch_metrics:
                    shared_state['batch_metrics'] = batch_metrics
                    self.logger.info(f"✅ Recovered batch metrics from pipeline_metadata")
        
            self._log_completion_summary(shared_state)
            
            return shared_state
            
        except Exception as e:
            self.logger.error(f"❌ Pipeline execution failed: {str(e)}")
            shared_state["pipeline_metadata"]["end_time"] = datetime.now(timezone.utc).isoformat()
            shared_state["pipeline_metadata"]["status"] = "failed"
            shared_state["pipeline_metadata"]["error"] = str(e)
            shared_state["pipeline_stage"] = "failed"
            raise


    def _log_completion_summary(self, shared_state: Dict[str, Any]):
        """Log a summary of pipeline execution results"""
        raw_captures = shared_state.get('raw_captures', [])
        extracted_concepts = shared_state.get('extracted_concepts', {})
        knowledge_graph = shared_state.get('knowledge_graph', {})
        historical_connections = shared_state.get('historical_connections', {})
        notion_generation = shared_state.get('notion_generation', {})

        batch_metrics = shared_state.get('batch_metrics', {})

        self.logger.info("✅ Pipeline execution completed successfully")
        self.logger.info(f"   → Processed {len(raw_captures)} captures")
        self.logger.info(f"   → Extracted {len(extracted_concepts.get('learning_concepts', []))} key concepts")

        if batch_metrics:
            api_calls_saved = batch_metrics.get('api_calls_saved', 0)
            cache_hit_rate = batch_metrics.get('cache_hit_rate', 0)
            self.logger.info(f"   → 🚀 Batch optimization: {api_calls_saved} API calls saved ({cache_hit_rate:.1f}% cache hit rate)")
        
        if knowledge_graph:
            nodes_created = knowledge_graph.get('nodes_created', {})
            total_nodes = sum(nodes_created.values())
            self.logger.info(f"   → Created {total_nodes} knowledge graph nodes")
        
        if historical_connections:
            connections = historical_connections.get('total_connections_found', 0)
            self.logger.info(f"   → Found {connections} historical knowledge connections")

        if notion_generation and notion_generation.get('master_session_url'):
            self.logger.info(f"   → Generated Notion page: {notion_generation['master_session_url']}")

    
    def run_single_node(self, node_name: str, input_captures: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a single node for testing purposes.
        
        Args:
            node_name: Name of the node to execute
            input_captures: Input captures in minimal format
            
        Returns:
            Processed shared state from single node
        """
        if not input_captures:
            raise ValueError("No input captures provided")
        
        user_id = input_captures[0].get('user_id', 'test_user')
        session_id = f"test_{node_name}_{int(datetime.now(timezone.utc).timestamp())}"
        
        self.logger.info(f"🧪 Testing single node: {node_name}")
        self.logger.info(f"   Session ID: {session_id}")
        
        shared_state = {
            "session_id": session_id,
            "user_id": user_id,
            "pipeline_stage": f"testing_{node_name}",
            "raw_input": input_captures,
            "pipeline_metadata": {
                "start_time": datetime.now(timezone.utc).isoformat(),
                "test_mode": True,
                "target_node": node_name,
                "input_format": "minimal_capture"
            }
        }
        
        try:
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
            
            self.logger.info(f"✅ Single node execution completed: {node_name}")
            return shared_state
            
        except Exception as e:
            self.logger.error(f"❌ Single node execution failed: {str(e)}")
            raise


def create_sample_minimal_input() -> List[Dict[str, Any]]:
    """
    Create sample input in the minimal format
    """
    return [    
        {
            "content": "Machine learning is a method of data analysis that automates analytical model building. It uses algorithms that iteratively learn from data, allowing computers to find hidden insights without being explicitly programmed where to look.",
            "user_id": "learner_alex",
            "source_url": "https://example.com/ml-basics",
            "title": "Machine Learning Fundamentals",
            "intent": "learn",
            "user_note": "Need to understand this for my AI course"
        },
        {
            "content": "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) that work together to solve specific problems through learning from data.",
            "user_id": "learner_alex",
            "source_url": "https://example.com/neural-networks",
            "title": "Introduction to Neural Networks",
            "intent": "research"
        },
        {
            "content": "Deep learning is a subset of machine learning that uses neural networks with three or more layers. These neural networks attempt to simulate the behavior of the human brain to learn from large amounts of data.",
            "user_id": "learner_alex",
            "source_url": "https://example.com/deep-learning",
            "title": "Deep Learning Explained",
            "intent": "learn"
        }
    ]


def print_pipeline_summary(result: Dict[str, Any]):
    """Print a clean summary of pipeline results"""
    print("\n" + "="*60)
    print("🧠 BROWSERBUD PIPELINE RESULTS")
    print("="*60)
    
    metadata = result.get("pipeline_metadata", {})
    print(f"📊 Session ID: {result.get('session_id', 'Unknown')}")
    print(f"📊 Status: {metadata.get('status', 'Unknown')}")
    print(f"📊 Processing Time: {_calculate_processing_time(metadata):.2f} seconds")
    print(f"📊 Input Format: {metadata.get('input_format', 'unknown')}")

    batch_metrics = result.get('batch_metrics', {})
    if batch_metrics:
        api_calls_saved = batch_metrics.get('api_calls_saved', 0)
        cache_hit_rate = batch_metrics.get('cache_hit_rate', 0)
        total_processed = batch_metrics.get('total_captures_processed', 0)
        
        print(f"\n🚀 BATCH OPTIMIZATION RESULTS:")
        print(f"   ✅ API Calls Saved: {api_calls_saved}")
        print(f"   ✅ Cache Hit Rate: {cache_hit_rate:.1f}%")
        print(f"   ✅ Total Captures Processed: {total_processed}")
        
        if api_calls_saved > 0:
            print(f"   💰 Cost Savings: ~{api_calls_saved * 0.01:.2f} USD (estimated)")
    
    
    # Capture ingestion results
    raw_captures = result.get("raw_captures", [])
    if raw_captures:
        print(f"\n📥 CAPTURE PROCESSING:")
        print(f"   ✅ Successfully processed: {len(raw_captures)} captures")
        
        # Show sample of processed content
        for i, capture in enumerate(raw_captures[:2]):
            title = capture.get('title', f'Capture {i+1}')
            content_preview = capture.get('content', '')[:100] + "..."
            print(f"   📄 {title}")
            print(f"      Content: {content_preview}")
    
    # Content analysis results
    extracted_concepts = result.get("extracted_concepts", {})
    if extracted_concepts:
        print(f"\n🧠 CONTENT ANALYSIS:")
        learning_concepts = extracted_concepts.get('learning_concepts', [])
        session_theme = extracted_concepts.get('session_theme', 'unknown')
        complexity = extracted_concepts.get('complexity_assessment', {}).get('overall_level', 'unknown')
        
        print(f"   🎯 Key Learning Concepts: {len(learning_concepts)}")
        if learning_concepts:
            print(f"      Top concepts: {', '.join(learning_concepts[:3])}")
        print(f"   🎯 Session Theme: {session_theme.replace('_', ' ').title()}")
        print(f"   🎯 Complexity Level: {complexity.title()}")
        
        key_terms = extracted_concepts.get('key_terms', {})
        if key_terms:
            print(f"   📚 Key Terms Identified: {len(key_terms)}")
    
    # Knowledge graph results
    knowledge_graph = result.get("knowledge_graph", {})
    if knowledge_graph:
        print(f"\n🕸️ KNOWLEDGE GRAPH:")
        nodes_created = knowledge_graph.get('nodes_created', {})
        relationships = knowledge_graph.get('relationships_created', 0)
        
        total_nodes = sum(nodes_created.values())
        print(f"   🔗 Total Nodes Created: {total_nodes}")
        for node_type, count in nodes_created.items():
            if count > 0:
                print(f"      {node_type.title()}: {count}")
        print(f"   🔗 Relationships Created: {relationships}")
        
        metrics = knowledge_graph.get('metrics', {})
        if metrics.get('graph_density'):
            print(f"   🔗 Graph Density: {metrics['graph_density']:.3f}")
    
    # Historical analysis results
    historical_connections = result.get('historical_connections', {})
    knowledge_gaps = result.get('knowledge_gaps', [])
    learning_recommendations = result.get('learning_recommendations', [])
    
    if historical_connections or knowledge_gaps or learning_recommendations:
        print(f"\n📈 LEARNING INSIGHTS:")
        connections_found = historical_connections.get('total_connections_found', 0)
        print(f"   🔍 Historical Connections Found: {connections_found}")
        print(f"   ⚠️ Knowledge Gaps Identified: {len(knowledge_gaps)}")
        print(f"   💡 Learning Recommendations: {len(learning_recommendations)}")
        
        # Show high-priority recommendations
        high_priority = [r for r in learning_recommendations if r.get('priority') == 'high']
        if high_priority:
            print(f"\n   🚨 High Priority Actions:")
            for rec in high_priority[:2]:
                action = rec.get('action', rec.get('recommended_action', 'No action specified'))
                print(f"      • {action}")
        
        # Show critical knowledge gaps
        critical_gaps = [gap for gap in knowledge_gaps if gap.get('priority') == 'high']
        if critical_gaps:
            print(f"\n   📚 Critical Knowledge Gaps:")
            for gap in critical_gaps[:2]:
                missing = gap.get('missing_concept', 'Unknown concept')
                action = gap.get('recommended_action', 'Study recommended')
                print(f"      • {missing}: {action}")
    
    # Notion generation results
    notion_generation = result.get("notion_generation", {})
    if notion_generation:
        print(f"\n📄 NOTION INTEGRATION:")
        creation_summary = notion_generation.get('creation_summary', {})
        session_url = notion_generation.get('master_session_url')
        
        print(f"   📝 Session Page Created: {'✅' if creation_summary.get('session_created') else '❌'}")
        print(f"   📝 Total Pages Generated: {creation_summary.get('total_pages', 0)}")
        print(f"   📝 Concepts Documented: {creation_summary.get('concepts_created', 0)}")
        print(f"   📝 Sources Cataloged: {creation_summary.get('sources_created', 0)}")
        
        if session_url:
            print(f"\n   🔗 Your Notion Session:")
            print(f"      {session_url}")
            print(f"\n   💡 Open this URL to explore your AI-processed learning session!")
    
    print("\n" + "="*60)
    print("✨ Pipeline execution complete!")
    
    if notion_generation and notion_generation.get('session_page_url'):
        print("\n🎯 NEXT STEPS:")
        print("1. 📖 Review your Notion session page for structured insights")
        print("2. 🔍 Explore the concept and source databases")
        print("3. 📋 Address the identified knowledge gaps")
        print("4. ✅ Follow the high-priority learning recommendations")
        print("\n🚀 Your AI-powered learning journey continues!")
    else:
        print("\n💡 Consider setting up Notion integration for rich, structured output!")


def _calculate_processing_time(metadata: Dict[str, Any]) -> float:
    """Calculate processing time from metadata"""
    try:
        start_time = metadata.get('start_time')
        end_time = metadata.get('end_time')
        
        if start_time and end_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            return (end_dt - start_dt).total_seconds()
    except Exception:
        pass
    
    return 0.0

    
def main():
    """Main entry point for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="BrowserBud Pipeline")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--input", help="Path to input JSON file with capture data")
    parser.add_argument("--output", help="Path to output JSON file for results")
    parser.add_argument("--node", help="Run single node only (for testing)")
    parser.add_argument("--sample", action="store_true", help="Use built-in sample data")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    try:
        pipeline = NoteGenerationPipeline(args.config)
        
        # Override log level if verbose requested
        if args.verbose:
            pipeline.config.log_level = "DEBUG"
            pipeline.setup_logging()
        
        if args.sample:
            input_captures = create_sample_minimal_input()
            print("📝 Using sample minimal input data")
        elif args.input:
            with open(args.input, 'r', encoding='utf-8') as f:
                input_captures = json.load(f)
            print(f"📁 Loaded input from: {args.input}")
        else:
            print("❌ Error: Must specify --input file or --sample flag")
            sys.exit(1)
        
        print(f"🎯 Processing {len(input_captures)} captures...")
        
        for i, capture in enumerate(input_captures):
            if not capture.get('content') or not capture.get('user_id'):
                print(f"❌ Error: Capture {i} missing required fields (content, user_id)")
                sys.exit(1)
        
        if args.node:
            print(f"🧪 Testing single node: {args.node}")
            result = pipeline.run_single_node(args.node, input_captures)
        else:
            print("🚀 Executing complete pipeline...")
            result = pipeline.run(input_captures)
        
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, default=str)
            
            print(f"💾 Results saved to: {output_path}")
        else:
            print_pipeline_summary(result)
    
    except Exception as e:
        print(f"❌ Pipeline execution failed: {str(e)}")
        sys.exit(1)



if __name__ == "__main__":
    print("🎯 BROWSERBUD PIPELINE")
    print("="*50)
    print("\n📝 INPUT FORMAT:")
    print("""
    {
        "content": "Your learning content here...",
        "user_id": "your_user_id",
        "source_url": "https://source.com",  # Optional
        "title": "Content Title",  # Optional
        "intent": "learn",  # Optional: learn|research|reference|archive
        "user_note": "Personal context"  # Optional
    }
    """)
    main()