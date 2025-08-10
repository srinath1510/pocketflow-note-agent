#!/usr/bin/env python3
"""
Test script for the AI Note Generation Pipeline
Works with .env configuration and tests the complete pipeline
"""

import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import NoteGenerationPipeline, create_sample_minimal_input


def check_environment():
    """Check if environment is properly configured."""
    print("🔧 Environment Configuration Check")
    print("=" * 50)
    
    required_vars = {
        'ANTHROPIC_API_KEY': 'LLM provider',
        'NOTION_TOKEN': 'Notion integration',
        'NEO4J_URI': 'Knowledge graph database',
        'NEO4J_USER': 'Neo4j username',
        'NEO4J_PASSWORD': 'Neo4j password'
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'TOKEN' in var or 'PASSWORD' in var:
                display_value = f"{'*' * 8}...{value[-4:]}" if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: Not set ({description})")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with the required variables.")
        return False
    
    print("✅ Environment configuration looks good!")
    return True


def test_neo4j_connection():
    """Test Neo4j database connection."""
    try:
        from nodes.knowledge_graph import test_neo4j_connection
        return test_neo4j_connection()
    except ImportError:
        # Fallback test
        try:
            from neo4j import GraphDatabase
            uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            user = os.getenv('NEO4J_USER', 'neo4j')
            password = os.getenv('NEO4J_PASSWORD', 'smartnotes123')
            
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                result = session.run("RETURN 'Connected!' as message")
                message = result.single()['message']
                print(f"✅ Neo4j connection successful: {message}")
            driver.close()
            return True
        except Exception as e:
            print(f"❌ Neo4j connection failed: {e}")
            print("   Make sure Neo4j is running: docker-compose up -d neo4j")
            return False


def test_minimal_input_format():
    """Test the minimal input format."""
    print("\nTesting Minimal Input Format")
    print("=" * 50)
    
    # Create minimal format test data
    minimal_captures = [
        {
            "content": "Machine learning is a method of data analysis that automates analytical model building. It uses algorithms that iteratively learn from data, allowing computers to find hidden insights without being explicitly programmed where to look.",
            "user_id": "test_learner_123",
            "source_url": "https://example.com/ml-basics",
            "title": "Machine Learning Fundamentals",
            "intent": "learn",
            "user_note": "Need to understand this for my AI course"
        },
        {
            "content": "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) that work together to solve specific problems through learning from data patterns.",
            "user_id": "test_learner_123",
            "source_url": "https://example.com/neural-networks",
            "title": "Introduction to Neural Networks",
            "intent": "research"
        },
        {
            "content": "Deep learning is a subset of machine learning that uses neural networks with three or more layers. These neural networks attempt to simulate the behavior of the human brain to learn from large amounts of data.",
            "user_id": "test_learner_123",
            "source_url": "https://example.com/deep-learning",
            "title": "Deep Learning Explained",
            "intent": "learn"
        }
    ]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        print(f"📝 Testing with {len(minimal_captures)} minimal captures...")
        result = pipeline.run(minimal_captures)
        
        print(f"✅ Minimal format test completed successfully!")
        print(f"   Session ID: {result['session_id']}")
        print(f"   User ID: {result['user_id']}")
        print(f"   Pipeline Status: {result['pipeline_metadata']['status']}")
        
        # Verify each stage worked
        stages_completed = []
        if 'raw_captures' in result:
            stages_completed.append(f"Capture Ingestion ({len(result['raw_captures'])} captures)")
        if 'extracted_concepts' in result:
            concepts = result['extracted_concepts']
            stages_completed.append(f"Content Analysis ({len(concepts.get('learning_concepts', []))} concepts)")
        if 'knowledge_graph' in result:
            kg = result['knowledge_graph']
            nodes = sum(kg.get('nodes_created', {}).values())
            stages_completed.append(f"Knowledge Graph ({nodes} nodes)")
        if 'historical_connections' in result:
            connections = result['historical_connections']['total_connections_found']
            stages_completed.append(f"Historical Analysis ({connections} connections)")
        if 'notion_generation' in result:
            pages = result['notion_generation']['creation_summary']['total_pages']
            stages_completed.append(f"Notion Generation ({pages} pages)")
        
        print("   Pipeline Stages Completed:")
        for stage in stages_completed:
            print(f"     ✅ {stage}")
        
        # Check batch optimization
        if 'batch_metrics' in result:
            batch_metrics = result['batch_metrics']
            api_calls_saved = batch_metrics.get('api_calls_saved', 0)
            if api_calls_saved > 0:
                print(f"   🚀 Batch Optimization: {api_calls_saved} API calls saved!")
        
        # Save results
        save_test_results("minimal_format_test", result)
        return True
        
    except Exception as e:
        print(f"❌ Minimal format test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_capture_ingestion_node():
    """Test the Capture Ingestion node specifically."""
    print("\nTesting Capture Ingestion Node")
    print("=" * 50)
    
    # Test with minimal input format
    test_input = [
        {
            "content": "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            "user_id": "test_user_456",
            "source_url": "https://python.org/about",
            "title": "About Python Programming",
            "intent": "reference"
        }
    ]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        # Test single node execution
        result = pipeline.run_single_node("capture_ingestion", test_input)
        
        print(f"✅ Capture Ingestion test completed!")
        
        if "raw_captures" in result:
            captures = result["raw_captures"]
            print(f"   Processed: {len(captures)} capture(s)")
            
            for i, capture in enumerate(captures):
                metadata = capture.get('metadata', {})
                print(f"\n   Capture {i+1}:")
                print(f"     Content Length: {len(capture.get('content', ''))} chars")
                print(f"     Word Count: {metadata.get('word_count', 0)}")
                print(f"     Domain: {metadata.get('domain', 'unknown')}")
                print(f"     Category: {metadata.get('content_category', 'unknown')}")
                print(f"     Knowledge Level: {metadata.get('knowledge_level', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Capture Ingestion test failed: {str(e)}")
        return False


def test_content_analysis_node():
    """Test the Content Analysis node with LLM."""
    print("\nTesting Content Analysis Node (LLM)")
    print("=" * 50)
    
    # Test data for content analysis
    test_input = [
        {
            "content": "Machine learning algorithms can be categorized into supervised learning, unsupervised learning, and reinforcement learning. Supervised learning uses labeled training data to learn a mapping from inputs to outputs.",
            "user_id": "test_analyst_789",
            "source_url": "https://ml-guide.com/basics",
            "title": "ML Algorithm Categories",
            "intent": "learn"
        },
        {
            "content": "Neural networks consist of layers of interconnected nodes called neurons. Each connection has a weight that adjusts during training through backpropagation algorithm to minimize prediction errors.",
            "user_id": "test_analyst_789",
            "source_url": "https://neural-nets.org/intro",
            "title": "Neural Network Basics",
            "intent": "research"
        }
    ]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run through capture ingestion first, then content analysis
        result = pipeline.run_single_node("content_analysis", test_input)
        
        print(f"✅ Content Analysis test completed!")
        
        if "extracted_concepts" in result:
            concepts = result["extracted_concepts"]
            
            print(f"\n   Extracted Results:")
            learning_concepts = concepts.get('learning_concepts', [])
            print(f"     Learning Concepts: {len(learning_concepts)}")
            if learning_concepts:
                print(f"       Examples: {learning_concepts[:3]}")
            
            key_terms = concepts.get('key_terms', {})
            print(f"     Key Terms: {len(key_terms)}")
            if key_terms:
                print(f"       Examples: {list(key_terms.keys())[:3]}")
            
            session_theme = concepts.get('session_theme', 'unknown')
            print(f"     Session Theme: {session_theme}")
            
            complexity = concepts.get('complexity_assessment', {})
            print(f"     Complexity Level: {complexity.get('overall_level', 'unknown')}")
        
        # Check batch metrics
        if 'batch_metrics' in result:
            batch_metrics = result['batch_metrics']
            print(f"\n   Batch Optimization:")
            print(f"     API Calls Made: {batch_metrics.get('api_calls_made', 0)}")
            print(f"     API Calls Saved: {batch_metrics.get('api_calls_saved', 0)}")
            print(f"     Cache Hit Rate: {batch_metrics.get('cache_hit_rate', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Content Analysis test failed: {str(e)}")
        print("   Make sure your ANTHROPIC_API_KEY is properly set in .env")
        return False


def test_knowledge_graph_node():
    """Test the Knowledge Graph node with Neo4j."""
    print("\nTesting Knowledge Graph Node (Neo4j)")
    print("=" * 50)
    
    # First check Neo4j connection
    if not test_neo4j_connection():
        print("❌ Skipping Knowledge Graph test - Neo4j not available")
        return False
    
    test_input = [
        {
            "content": "Artificial intelligence encompasses machine learning, natural language processing, computer vision, and robotics. These fields work together to create intelligent systems.",
            "user_id": "test_researcher_101",
            "source_url": "https://ai-overview.com",
            "title": "AI Field Overview",
            "intent": "research"
        }
    ]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run through all prerequisite nodes first
        result = pipeline.run_single_node("knowledge_graph", test_input)
        
        print(f"✅ Knowledge Graph test completed!")
        
        if "knowledge_graph" in result:
            kg = result["knowledge_graph"]
            
            print(f"\n   Knowledge Graph Results:")
            nodes_created = kg.get('nodes_created', {})
            print(f"     Concepts: {nodes_created.get('concepts', 0)}")
            print(f"     Entities: {nodes_created.get('entities', 0)}")
            print(f"     Topics: {nodes_created.get('topics', 0)}")
            print(f"     Resources: {nodes_created.get('resources', 0)}")
            
            relationships = kg.get('relationships_created', 0)
            print(f"     Relationships: {relationships}")
            
            metrics = kg.get('metrics', {})
            if metrics:
                print(f"     Graph Density: {metrics.get('graph_density', 0):.4f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge Graph test failed: {str(e)}")
        return False


def test_historical_knowledge_node():
    """Test the Historical Knowledge Retrieval node."""
    print("\nTesting Historical Knowledge Node")
    print("=" * 50)
    
    # Run a session first to populate the knowledge graph
    setup_input = [
        {
            "content": "Python programming basics: variables, functions, classes, and modules. Object-oriented programming principles in Python.",
            "user_id": "test_student_202",
            "source_url": "https://python-basics.com",
            "title": "Python Programming Basics",
            "intent": "learn"
        }
    ]
    
    # Then run another session to test historical connections
    test_input = [
        {
            "content": "Advanced Python concepts: decorators, generators, context managers, and metaclasses. Building on object-oriented programming fundamentals.",
            "user_id": "test_student_202",
            "source_url": "https://advanced-python.com",
            "title": "Advanced Python Concepts",
            "intent": "learn"
        }
    ]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run setup session
        print("   Setting up knowledge base...")
        pipeline.run(setup_input)
        
        # Run test session
        print("   Testing historical connections...")
        result = pipeline.run_single_node("historical_knowledge", test_input)
        
        print(f"✅ Historical Knowledge test completed!")
        
        if "historical_connections" in result:
            connections = result["historical_connections"]
            total_connections = connections.get('total_connections_found', 0)
            print(f"     Total Connections Found: {total_connections}")
        
        if "knowledge_gaps" in result:
            gaps = result["knowledge_gaps"]
            print(f"     Knowledge Gaps Identified: {len(gaps)}")
        
        if "learning_recommendations" in result:
            recommendations = result["learning_recommendations"]
            print(f"     Learning Recommendations: {len(recommendations)}")
            
            # Show high priority recommendations
            high_priority = [r for r in recommendations if r.get('priority') == 'high']
            if high_priority:
                print(f"     High Priority Actions:")
                for rec in high_priority[:2]:
                    print(f"       - {rec.get('action', 'No action specified')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Historical Knowledge test failed: {str(e)}")
        return False


def test_notion_generation_node():
    """Test the Notion Note Generation node."""
    print("\nTesting Notion Generation Node")
    print("=" * 50)
    
    test_input = [
        {
            "content": "React hooks revolutionized functional components by allowing state management and lifecycle methods. useState and useEffect are the most commonly used hooks.",
            "user_id": "test_developer_303",
            "source_url": "https://react-hooks.dev",
            "title": "React Hooks Guide",
            "intent": "learn"
        }
    ]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run the full pipeline to test Notion generation
        result = pipeline.run_single_node("notion_generation", test_input)
        
        print(f"✅ Notion Generation test completed!")
        
        if "notion_generation" in result:
            notion = result["notion_generation"]
            
            print(f"\n   Notion Results:")
            creation_summary = notion.get('creation_summary', {})
            print(f"     Pages Created: {creation_summary.get('total_pages', 0)}")
            print(f"     Topics Covered: {len(creation_summary.get('topics_covered', []))}")
            print(f"     Concepts Documented: {creation_summary.get('concepts_created', 0)}")
            
            session_url = notion.get('master_session_url')
            if session_url:
                print(f"     Session Page URL: {session_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Notion Generation test failed: {str(e)}")
        print("   Make sure your NOTION_TOKEN is properly set in .env")
        return False


def test_complete_pipeline():
    """Test the complete pipeline end-to-end."""
    print("\nTesting Complete Pipeline (End-to-End)")
    print("=" * 50)
    
    # Use the sample data from main.py
    sample_data = create_sample_minimal_input()
    
    pipeline = NoteGenerationPipeline()
    
    try:
        print(f"🚀 Running complete pipeline with {len(sample_data)} captures...")
        result = pipeline.run(sample_data)
        
        print(f"✅ Complete pipeline test succeeded!")
        print(f"   Session ID: {result['session_id']}")
        print(f"   User ID: {result['user_id']}")
        
        # Print comprehensive summary
        metadata = result.get('pipeline_metadata', {})
        print(f"\n   Pipeline Execution:")
        print(f"     Status: {metadata.get('status', 'unknown')}")
        print(f"     Processing Time: {_calculate_processing_time(metadata):.2f} seconds")
        
        # Stage results
        stages = [
            ("Capture Ingestion", "raw_captures", lambda x: len(x)),
            ("Content Analysis", "extracted_concepts", lambda x: len(x.get('learning_concepts', []))),
            ("Knowledge Graph", "knowledge_graph", lambda x: sum(x.get('nodes_created', {}).values())),
            ("Historical Analysis", "historical_connections", lambda x: x.get('total_connections_found', 0)),
            ("Notion Generation", "notion_generation", lambda x: x.get('creation_summary', {}).get('total_pages', 0))
        ]
        
        print(f"\n   Stage Results:")
        for stage_name, key, extract_func in stages:
            if key in result:
                value = extract_func(result[key])
                print(f"     {stage_name}: {value}")
            else:
                print(f"     {stage_name}: Not completed")
        
        # Batch optimization results
        if 'batch_metrics' in result:
            batch_metrics = result['batch_metrics']
            api_calls_saved = batch_metrics.get('api_calls_saved', 0)
            cache_hit_rate = batch_metrics.get('cache_hit_rate', 0)
            print(f"\n   Optimization Results:")
            print(f"     API Calls Saved: {api_calls_saved}")
            print(f"     Cache Hit Rate: {cache_hit_rate:.1f}%")
        
        # Notion output
        if 'notion_generation' in result:
            notion = result['notion_generation']
            session_url = notion.get('master_session_url')
            if session_url:
                print(f"\n   🎯 Notion Session Created:")
                print(f"     URL: {session_url}")
                print(f"     Open this URL to see your AI-processed learning session!")
        
        # Save complete results
        save_test_results("complete_pipeline_test", result)
        
        return True
        
    except Exception as e:
        print(f"❌ Complete pipeline test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def _calculate_processing_time(metadata):
    """Calculate processing time from metadata."""
    try:
        start_time = metadata.get('start_time')
        end_time = metadata.get('end_time')
        
        if start_time and end_time:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            return (end_dt - start_dt).total_seconds()
    except Exception:
        pass
    
    return 0.0


def save_test_results(test_name: str, result_data: dict):
    """Save test results to a JSON file for inspection."""
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{test_name}_result.json"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, default=str)
        
        print(f"   📁 Results saved to: {output_file}")
    except Exception as e:
        print(f"   ⚠️ Could not save results: {e}")


def main():
    """Run all pipeline tests."""
    print("🚀 AI Learning Pipeline Comprehensive Test Suite")
    print("=" * 60)
    
    # Check environment first
    if not check_environment():
        print("\n❌ Environment check failed. Please configure your .env file.")
        print("\nRequired .env variables:")
        print("  ANTHROPIC_API_KEY=your_anthropic_key")
        print("  NOTION_TOKEN=your_notion_token")
        print("  NEO4J_URI=bolt://localhost:7687")
        print("  NEO4J_USER=neo4j")
        print("  NEO4J_PASSWORD=smartnotes123")
        return
    
    print(f"\n🧪 Running Pipeline Tests...")
    
    # Define test suite
    tests = [
        ("Environment Check", check_environment),
        ("Neo4j Connection", test_neo4j_connection),
        ("Minimal Input Format", test_minimal_input_format),
        ("Capture Ingestion Node", test_capture_ingestion_node),
        ("Content Analysis Node", test_content_analysis_node),
        ("Knowledge Graph Node", test_knowledge_graph_node),
        ("Historical Knowledge Node", test_historical_knowledge_node),
        ("Notion Generation Node", test_notion_generation_node),
        ("Complete Pipeline", test_complete_pipeline)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results[test_name] = "PASSED" if success else "FAILED"
            print(f"{'✅' if success else '❌'} {test_name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            print(f"💥 {test_name} crashed: {str(e)}")
            results[test_name] = "ERROR"
    
    # Final summary
    print(f"\n{'='*60}")
    print("🏁 FINAL TEST SUMMARY")
    print("=" * 60)
    
    for test_name, status in results.items():
        status_emoji = "✅" if status == "PASSED" else "❌"
        print(f"{status_emoji} {test_name}: {status}")
    
    passed = sum(1 for status in results.values() if status == "PASSED")
    total = len(results)
    
    print(f"\n📊 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("Your AI Learning Pipeline is working perfectly!")
        print("\n🚀 Next Steps:")
        print("  1. Try with your own learning content")
        print("  2. Check your Notion workspace for generated pages")
        print("  3. Explore the Neo4j database at http://localhost:7474")
        print("  4. Review the knowledge connections and recommendations")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("\n🔧 Troubleshooting:")
        
        if results.get("Neo4j Connection") != "PASSED":
            print("  • Neo4j: Start with 'docker-compose up -d neo4j'")
        
        if results.get("Content Analysis Node") != "PASSED":
            print("  • LLM: Check ANTHROPIC_API_KEY in .env file")
        
        if results.get("Notion Generation Node") != "PASSED":
            print("  • Notion: Check NOTION_TOKEN in .env file")
        
        print("\n📋 Check the detailed output above for specific error messages.")


if __name__ == "__main__":
    main()