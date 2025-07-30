#!/usr/bin/env python3
"""
Test script for the AI Note Generation Pipeline
Demonstrates how to use the Capture Ingestion node and full pipeline
"""

import json
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import NoteGenerationPipeline, load_sample_data


def test_capture_ingestion_single():
    """Test the Capture Ingestion node with a single capture."""
    print("Testing Capture Ingestion Node - Single Capture")
    print("=" * 50)
    
    # Sample data for a research article
    sample_data = {
        "url": "https://arxiv.org/abs/2023.01234",
        "content": """<html>
        <head><title>Transformer Architecture Improvements</title></head>
        <body>
            <h1>Transformer Architecture Improvements</h1>
            <div class="abstract">
                <h2>Abstract</h2>
                <p>This paper presents novel improvements to transformer architectures 
                for better performance on natural language understanding tasks.</p>
            </div>
            <h2>1. Introduction</h2>
            <p>Transformer models have revolutionized <code>natural language processing</code> 
            since their introduction in 2017.</p>
            <h2>2. Methodology</h2>
            <p>We propose three key improvements:</p>
            <ul>
                <li>Enhanced attention mechanism</li>
                <li>Improved positional encoding</li>
                <li>Novel layer normalization technique</li>
            </ul>
            <p>For more details, see our <a href="https://github.com/example/repo">code repository</a> 
            and the <a href="#references">references</a> section.</p>
            <h2>References</h2>
            <p>[1] Vaswani et al., "Attention is All You Need", NIPS 2017</p>
        </body>
        </html>""",
        "timestamp": "2025-06-16T10:30:00Z",
        "selected_text": "Enhanced attention mechanism",
        "highlights": ["Enhanced attention mechanism", "Novel layer normalization technique"],
        "context_before": "We propose three key improvements: ",
        "context_after": " Improved positional encoding",
        "selection_start_offset": 1250,
        "selection_end_offset": 1278,
        "relative_position": 0.6,
        "dwell_time": 180000,
        "scroll_depth": 0.7,
        "viewport_size": "1920x1080",
        "user_agent": "Mozilla/5.0 (Test Browser)",
        "trigger": "context_menu",
        "intent": "research_capture"
    }
    
    # Initialize pipeline
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run only the capture ingestion node
        result = pipeline.run_single_node("capture_ingestion", sample_data)
        
        # Display results
        print(f"✅ Processing completed successfully!")
        print(f"Session ID: {result['session_id']}")
        
        if "raw_captures" in result:
            captures = result["raw_captures"]
            print(f"Processed {len(captures)} capture(s)")
            
            for i, capture in enumerate(captures):
                print(f"\nCapture {i+1}:")
                print(f"  ID: {capture['id']}")
                print(f"  Title: {capture['metadata']['page_title']}")
                print(f"  URL: {capture['url']}")
                print(f"  Content Length: {len(capture['content'])} characters")
                print(f"  Word Count: {capture['metadata']['word_count']}")
                print(f"  Content Category: {capture['metadata']['content_category']}")
                print(f"  Knowledge Level: {capture['metadata']['knowledge_level']}")
                print(f"  Domain: {capture['metadata']['domain']}")
                print(f"  Headings Found: {len(capture['metadata']['heading_hierarchy'])}")
                print(f"  Links Found: {capture['metadata']['link_count']}")
                print(f"  Has Code: {capture['metadata']['has_code']}")
                print(f"  Citations: {capture['metadata']['citations']}")
                
                if capture['highlights']:
                    print(f"  Highlights: {capture['highlights']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False


def test_content_analysis():
    """Test the Content Analysis node with LLM extraction."""
    print("\nTesting Content Analysis Node - LLM Concept Extraction")
    print("=" * 50)
    
    # Prepare test data
    test_data = [
        {
            "url": "https://docs.python.org/3/library/asyncio.html",
            "content": """<html>
            <head><title>asyncio — Asynchronous I/O</title></head>
            <body>
                <h1>asyncio — Asynchronous I/O</h1>
                <p>The asyncio module provides infrastructure for writing single-threaded concurrent code 
                using coroutines, multiplexing I/O access over sockets and other resources.</p>
                <h2>Key Concepts</h2>
                <p>Event loops run asynchronous tasks and callbacks. Coroutines are special functions 
                that can be paused and resumed. Tasks are used to schedule coroutines concurrently.</p>
                <pre><code>import asyncio
                
async def main():
    print('Hello')
    await asyncio.sleep(1)
    print('World')

asyncio.run(main())</code></pre>
            </body>
            </html>""",
            "timestamp": "2025-06-16T14:15:30Z",
            "selected_text": "Event loops run asynchronous tasks",
            "highlights": ["Event loops", "Coroutines", "Tasks"]
        },
        {
            "url": "https://example.com/machine-learning-basics",
            "content": """<html>
            <head><title>Introduction to Machine Learning</title></head>
            <body>
                <h1>Introduction to Machine Learning</h1>
                <p>Machine learning is a subset of artificial intelligence that enables systems 
                to learn and improve from experience without being explicitly programmed.</p>
                <h2>Types of Machine Learning</h2>
                <ul>
                    <li>Supervised Learning: Learning with labeled data</li>
                    <li>Unsupervised Learning: Finding patterns in unlabeled data</li>
                    <li>Reinforcement Learning: Learning through interaction and rewards</li>
                </ul>
                <p>Popular algorithms include neural networks, decision trees, and support vector machines.</p>
            </body>
            </html>""",
            "timestamp": "2025-06-16T15:00:00Z",
            "selected_text": "neural networks, decision trees",
            "highlights": ["Supervised Learning", "neural networks"]
        }
    ]
    
    # Initialize pipeline
    pipeline = NoteGenerationPipeline()
    
    try:
        # First run capture ingestion
        ingestion_result = pipeline.run_single_node("capture_ingestion", test_data)
        
        # Then run content analysis
        result = pipeline.run_single_node("content_analysis", test_data)
        
        print(f"✅ Content analysis completed!")
        
        if "extracted_concepts" in result:
            concepts = result["extracted_concepts"]
            
            print(f"\nExtracted Concepts:")
            print(f"  Learning Concepts: {concepts.get('learning_concepts', [])[:5]}")
            print(f"  Key Terms: {list(concepts.get('key_terms', {}).keys())[:5]}")
            print(f"  Entities: {list(concepts.get('entities', {}).keys())[:5]}")
            print(f"  Session Theme: {concepts.get('session_theme', 'unknown')}")
            print(f"  Complexity: {concepts.get('complexity_assessment', {}).get('overall_level', 'unknown')}")
            
            if concepts.get('learning_goals'):
                print(f"  Learning Goals: {concepts['learning_goals'][:3]}")
            
            if concepts.get('knowledge_progression'):
                print(f"  Knowledge Progression: {concepts['knowledge_progression'][:3]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Content analysis test failed: {str(e)}")
        print(f"Make sure you have configured your LLM API key in .env file")
        return False
        

def test_knowledge_graph_node():
    """Test the Knowledge Graph node with Neo4j."""
    print("\nTesting Knowledge Graph Node - Neo4j Integration")
    print("=" * 50)
    
    # First check Neo4j connection
    print("Checking Neo4j connection...")
    if not test_neo4j_connection():
        print("❌ Neo4j is not available. Please start it with: docker-compose up -d")
        return False
    
    # Test data that includes extracted concepts
    test_data = [
        {
            "url": "https://example.com/python-tutorial",
            "content": """<html>
            <head><title>Python Programming Tutorial</title></head>
            <body>
                <h1>Python Programming Tutorial</h1>
                <p>Python is a high-level programming language known for its simplicity.</p>
                <h2>Core Concepts</h2>
                <ul>
                    <li>Variables and Data Types</li>
                    <li>Functions and Modules</li>
                    <li>Object-Oriented Programming</li>
                </ul>
            </body>
            </html>""",
            "timestamp": "2025-06-16T10:00:00Z",
            "selected_text": "Object-Oriented Programming",
            "highlights": ["Variables and Data Types", "Functions and Modules"]
        }
    ]
    
    # Initialize pipeline
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run through full pipeline up to knowledge graph
        print("Running full pipeline through Knowledge Graph node...")
        
        # You can run the full pipeline which now includes all three nodes
        result = pipeline.run(test_data)
        
        print(f"✅ Knowledge graph construction completed!")
        
        if "knowledge_graph" in result:
            kg = result["knowledge_graph"]
            
            print(f"\nKnowledge Graph Results:")
            print(f"  User ID: {kg.get('user_id', 'unknown')}")
            print(f"  Session ID: {kg.get('session_id', 'unknown')}")
            
            nodes = kg.get('nodes_created', {})
            print(f"\nNodes Created:")
            print(f"  Concepts: {nodes.get('concepts', 0)}")
            print(f"  Entities: {nodes.get('entities', 0)}")
            print(f"  Topics: {nodes.get('topics', 0)}")
            print(f"  Resources: {nodes.get('resources', 0)}")
            
            print(f"\nRelationships Created: {kg.get('relationships_created', 0)}")
            
            metrics = kg.get('metrics', {})
            if metrics:
                print(f"\nGraph Metrics:")
                print(f"  Total Concepts: {metrics.get('total_concepts', 0)}")
                print(f"  Total Entities: {metrics.get('total_entities', 0)}")
                print(f"  Graph Density: {metrics.get('graph_density', 0):.4f}")
                
                if metrics.get('most_connected_concepts'):
                    print(f"\nMost Connected Concepts:")
                    for concept in metrics['most_connected_concepts'][:3]:
                        print(f"    - {concept['concept']}: {concept['connections']} connections")
            
            insights = kg.get('insights', {})
            if insights:
                print(f"\nInsights:")
                if insights.get('isolated_concepts'):
                    print(f"  Isolated Concepts: {insights['isolated_concepts'][:3]}")
                if insights.get('concept_clusters'):
                    print(f"  Concept Clusters: {len(insights['concept_clusters'])}")
                if insights.get('session_focus'):
                    print(f"  Session Focus: {insights['session_focus'][:3]}")
        
        # Save results
        save_test_results("knowledge_graph_test", result)
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge graph test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_full_pipeline_with_knowledge_graph():
    """Test the complete pipeline with all three nodes."""
    print("\nTesting Full Pipeline - All Nodes")
    print("=" * 50)
    
    # Rich test data for full pipeline
    test_data = [
        {
            "url": "https://pytorch.org/tutorials/beginner/basics/intro.html",
            "content": """<html>
            <head><title>PyTorch Fundamentals</title></head>
            <body>
                <h1>Introduction to PyTorch</h1>
                <p>PyTorch is an open source machine learning framework that accelerates the path 
                from research prototyping to production deployment.</p>
                <h2>Core Concepts</h2>
                <p>PyTorch provides two high-level features:</p>
                <ul>
                    <li>Tensor computation with strong GPU acceleration</li>
                    <li>Deep neural networks built on automatic differentiation</li>
                </ul>
                <h2>Getting Started</h2>
                <pre><code>
import torch
import numpy as np

# Create a tensor
x = torch.tensor([[1, 2], [3, 4]])
print(x)
                </code></pre>
                <p>PyTorch tensors are similar to NumPy arrays but can be used on GPUs.</p>
            </body>
            </html>""",
            "timestamp": "2025-06-16T11:00:00Z",
            "selected_text": "Tensor computation with strong GPU acceleration",
            "highlights": ["PyTorch", "Tensor computation", "automatic differentiation"]
        },
        {
            "url": "https://example.com/deep-learning-guide",
            "content": """<html>
            <head><title>Deep Learning Guide</title></head>
            <body>
                <h1>Understanding Deep Learning</h1>
                <p>Deep learning is a subset of machine learning that uses neural networks 
                with multiple layers to progressively extract higher-level features from raw input.</p>
                <h2>Key Components</h2>
                <ul>
                    <li>Neural Networks: Interconnected nodes inspired by the human brain</li>
                    <li>Backpropagation: Algorithm for training neural networks</li>
                    <li>Activation Functions: Non-linear transformations like ReLU, Sigmoid</li>
                    <li>Loss Functions: Measure how wrong the model's predictions are</li>
                </ul>
                <p>Popular frameworks include TensorFlow, PyTorch, and Keras.</p>
            </body>
            </html>""",
            "timestamp": "2025-06-16T11:30:00Z",
            "selected_text": "Backpropagation: Algorithm for training neural networks",
            "highlights": ["Neural Networks", "Backpropagation", "ReLU, Sigmoid"]
        },
        {
            "url": "https://nvidia.com/cuda-programming",
            "content": """<html>
            <head><title>CUDA Programming Guide</title></head>
            <body>
                <h1>CUDA Programming for GPU Acceleration</h1>
                <p>CUDA is NVIDIA's parallel computing platform that enables dramatic increases 
                in computing performance by harnessing the power of the GPU.</p>
                <h2>CUDA and Deep Learning</h2>
                <p>Modern deep learning frameworks like PyTorch and TensorFlow use CUDA 
                for GPU acceleration, enabling faster training of neural networks.</p>
                <h3>Key Concepts</h3>
                <ul>
                    <li>CUDA Kernels: Functions that run on the GPU</li>
                    <li>Thread Blocks: Groups of threads that execute together</li>
                    <li>Shared Memory: Fast memory shared between threads in a block</li>
                </ul>
            </body>
            </html>""",
            "timestamp": "2025-06-16T12:00:00Z",
            "selected_text": "CUDA Kernels: Functions that run on the GPU",
            "highlights": ["CUDA", "GPU acceleration", "PyTorch and TensorFlow use CUDA"]
        }
    ]
    
    # Initialize pipeline
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run the complete pipeline
        result = pipeline.run(test_data)
        
        print(f"✅ Full pipeline execution completed!")
        print(f"Session ID: {result['session_id']}")
        print(f"Pipeline Stage: {result.get('pipeline_stage', 'unknown')}")
        
        # Display results from each node
        print("\n📊 Pipeline Results Summary:")
        
        # Capture Ingestion Results
        if "raw_captures" in result:
            print(f"\n1️⃣ Capture Ingestion:")
            print(f"   - Processed {len(result['raw_captures'])} captures")
            domains = set(c['metadata']['domain'] for c in result['raw_captures'])
            print(f"   - Domains: {list(domains)}")
        
        # Content Analysis Results
        if "extracted_concepts" in result:
            concepts = result["extracted_concepts"]
            print(f"\n2️⃣ Content Analysis:")
            print(f"   - Learning Concepts: {len(concepts.get('learning_concepts', []))}")
            print(f"   - Session Theme: {concepts.get('session_theme', 'unknown')}")
            print(f"   - Complexity: {concepts.get('complexity_assessment', {}).get('overall_level', 'unknown')}")
            print(f"   - Top Concepts: {concepts.get('learning_concepts', [])[:3]}")
        
        # Knowledge Graph Results
        if "knowledge_graph" in result:
            kg = result["knowledge_graph"]
            print(f"\n3️⃣ Knowledge Graph:")
            nodes = kg.get('nodes_created', {})
            total_nodes = sum(nodes.values())
            print(f"   - Total Nodes: {total_nodes}")
            print(f"   - Relationships: {kg.get('relationships_created', 0)}")
            
            metrics = kg.get('metrics', {})
            if metrics:
                print(f"   - Graph Density: {metrics.get('graph_density', 0):.4f}")
        
        # Save complete results
        save_test_results("full_pipeline_test", result)
        
        return True
        
    except Exception as e:
        print(f"❌ Full pipeline test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_knowledge_graph_persistence():
    """Test that the knowledge graph persists across sessions."""
    print("\nTesting Knowledge Graph Persistence")
    print("=" * 50)
    
    # First session data
    session1_data = [{
        "url": "https://example.com/session1",
        "content": """<html>
        <head><title>Introduction to Algorithms</title></head>
        <body>
            <h1>Introduction to Algorithms</h1>
            <p>Algorithms are step-by-step procedures for solving problems.</p>
            <p>Common algorithms include sorting, searching, and graph traversal.</p>
        </body>
        </html>""",
        "timestamp": "2025-06-16T09:00:00Z",
        "selected_text": "sorting, searching, and graph traversal",
        "highlights": ["Algorithms", "sorting", "searching"]
    }]
    
    # Second session data (related concepts)
    session2_data = [{
        "url": "https://example.com/session2",
        "content": """<html>
        <head><title>Advanced Sorting Algorithms</title></head>
        <body>
            <h1>Advanced Sorting Algorithms</h1>
            <p>Building on basic algorithms, we explore quicksort and mergesort.</p>
            <p>These sorting algorithms are more efficient for large datasets.</p>
        </body>
        </html>""",
        "timestamp": "2025-06-16T10:00:00Z",
        "selected_text": "quicksort and mergesort",
        "highlights": ["sorting algorithms", "quicksort", "mergesort"]
    }]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run first session
        print("Running first learning session...")
        result1 = pipeline.run(session1_data)
        
        if "knowledge_graph" in result1:
            kg1 = result1["knowledge_graph"]
            print(f"Session 1 - Concepts added: {kg1['nodes_created']['concepts']}")
        
        # Run second session
        print("\nRunning second learning session...")
        result2 = pipeline.run(session2_data)
        
        if "knowledge_graph" in result2:
            kg2 = result2["knowledge_graph"]
            metrics2 = kg2.get('metrics', {})
            
            print(f"\nSession 2 Results:")
            print(f"  New concepts added: {kg2['nodes_created']['concepts']}")
            print(f"  Total concepts in graph: {metrics2.get('total_concepts', 0)}")
            print(f"  Total relationships: {metrics2.get('total_edges', 0)}")
            
            # Check if concepts are connected
            insights = kg2.get('insights', {})
            if insights.get('concept_clusters'):
                print(f"\nConcept Clusters Found:")
                for cluster in insights['concept_clusters'][:2]:
                    print(f"  Hub: {cluster['hub']}")
                    print(f"  Related: {', '.join(cluster['related'][:3])}")
        
        print("\n✅ Knowledge graph persistence test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Persistence test failed: {str(e)}")
        return False

def test_capture_ingestion_batch():
    """Test the Capture Ingestion node with multiple captures."""
    print("\nTesting Capture Ingestion Node - Batch Processing")
    print("=" * 50)
    
    # Sample batch data
    batch_data = [
        {
            "url": "https://docs.python.org/3/library/asyncio.html",
            "content": """<html>
            <head><title>asyncio — Asynchronous I/O</title></head>
            <body>
                <h1>asyncio — Asynchronous I/O</h1>
                <p>The asyncio module provides infrastructure for writing single-threaded concurrent code.</p>
                <h2>Getting Started</h2>
                <pre><code>import asyncio
                
async def main():
    print('Hello')
    await asyncio.sleep(1)
    print('World')

asyncio.run(main())</code></pre>
                <h2>Event Loop</h2>
                <p>The event loop is the core of every asyncio application.</p>
            </body>
            </html>""",
            "timestamp": "2025-06-16T14:15:30Z",
            "selected_text": "asyncio.run(main())",
            "highlights": ["asyncio.run(main())"],
            "dwell_time": 95000,
            "scroll_depth": 0.45,
            "viewport_size": "1440x900",
            "trigger": "highlight",
            "intent": "code_reference"
        },
        {
            "url": "https://medium.com/@developer/microservices-guide",
            "content": """<html>
            <head><title>Microservices Guide</title></head>
            <body>
                <article>
                    <h1>Understanding Microservices</h1>
                    <div class="meta">Posted on March 15, 2023 by John Developer</div>
                    <p>Microservices architecture structures an application as loosely coupled services.</p>
                    <h2>Benefits</h2>
                    <ul>
                        <li><strong>Scalability</strong>: Scale individual services</li>
                        <li><strong>Technology diversity</strong>: Use different technologies</li>
                        <li><strong>Resilience</strong>: Isolated failures</li>
                    </ul>
                    <blockquote>
                        <p>"Microservices are not a silver bullet." - Martin Fowler</p>
                    </blockquote>
                </article>
            </body>
            </html>""",
            "timestamp": "2025-06-16T16:45:00Z",
            "selected_text": "Microservices are not a silver bullet",
            "highlights": ["Microservices are not a silver bullet"],
            "dwell_time": 240000,
            "scroll_depth": 0.85,
            "viewport_size": "1366x768",
            "trigger": "double_click",
            "intent": "quote_capture"
        }
    ]
    
    # Initialize pipeline
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run only the capture ingestion node with batch data
        result = pipeline.run_single_node("capture_ingestion", batch_data)
        
        # Display results
        print(f"✅ Batch processing completed successfully!")
        print(f"Session ID: {result['session_id']}")
        
        if "raw_captures" in result:
            captures = result["raw_captures"]
            print(f"Processed {len(captures)} capture(s)")
            
            # Summary statistics
            content_categories = {}
            total_word_count = 0
            domains = set()
            
            for capture in captures:
                category = capture['metadata']['content_category']
                content_categories[category] = content_categories.get(category, 0) + 1
                total_word_count += capture['metadata']['word_count']
                domains.add(capture['metadata']['domain'])
            
            print(f"\nBatch Summary:")
            print(f"  Total Word Count: {total_word_count}")
            print(f"  Average Words per Capture: {total_word_count // len(captures)}")
            print(f"  Unique Domains: {len(domains)}")
            print(f"  Content Categories: {dict(content_categories)}")
            print(f"  Domains: {list(domains)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch test failed: {str(e)}")
        return False

def test_invalid_data():
    """Test the Capture Ingestion node with invalid data."""
    print("\nTesting Capture Ingestion Node - Invalid Data Handling")
    print("=" * 50)
    
    # Test data with missing required fields
    invalid_data = [
        {
            "url": "https://example.com/valid",
            "content": "<html><body>Valid content</body></html>",
            "timestamp": "2025-06-16T10:00:00Z"
        },
        {
            # Missing URL
            "content": "<html><body>Missing URL</body></html>",
            "timestamp": "2025-06-16T10:00:00Z"
        },
        {
            "url": "https://example.com/missing-content",
            # Missing content
            "timestamp": "2025-06-16T10:00:00Z"
        },
        {
            "url": "https://example.com/missing-timestamp",
            "content": "<html><body>Missing timestamp</body></html>"
            # Missing timestamp
        }
    ]
    
    # Initialize pipeline
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run capture ingestion with invalid data
        result = pipeline.run_single_node("capture_ingestion", invalid_data)
        
        print(f"✅ Invalid data handling completed!")
        print(f"Session ID: {result['session_id']}")
        
        # Check how many captures were successfully processed
        if "raw_captures" in result:
            captures = result["raw_captures"]
            print(f"Successfully processed: {len(captures)} out of {len(invalid_data)} captures")
            
            for capture in captures:
                print(f"  ✓ {capture['metadata']['page_title']} ({capture['url']})")
        
        # Check processing metadata
        if "pipeline_metadata" in result and "capture_ingestion_summary" in result["pipeline_metadata"]:
            summary = result["pipeline_metadata"]["capture_ingestion_summary"]
            print(f"\nProcessing Summary:")
            print(f"  Total Input: {summary.get('total_input_captures', 0)}")
            print(f"  Successfully Processed: {summary.get('successfully_processed', 0)}")
            print(f"  Success Rate: {summary.get('processing_success_rate', 0):.2%}")
        
        return True
        
    except Exception as e:
        print(f"❌ Invalid data test failed: {str(e)}")
        return False

def save_test_results(test_name: str, result_data: dict):
    """Save test results to a JSON file for inspection."""
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{test_name}_result.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, default=str)
    
    print(f"📁 Test results saved to: {output_file}")


def main():
    """Run all tests."""
    print("🚀 Starting AI Note Generation Pipeline Tests")
    print("=" * 60)

    print("Environment Check:")
    print(f"  LLM Provider: {os.getenv('LLM_PROVIDER', 'not set')}")
    print(f"  Neo4j URI: {os.getenv('NEO4J_URI', 'not set')}")
    
    tests = [
        ("Neo4j Connection", lambda: test_neo4j_connection()),
        ("Single Capture", test_capture_ingestion_single),
        ("Batch Processing", test_capture_ingestion_batch),
        ("Invalid Data Handling", test_invalid_data),
        ("Content Analysis (LLM)", test_content_analysis),
        ("Knowledge Graph Node", test_knowledge_graph_node),
        ("Full Pipeline", test_full_pipeline_with_knowledge_graph),
        ("Knowledge Graph Persistence", test_knowledge_graph_persistence)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            success = test_func()
            results[test_name] = "PASSED" if success else "FAILED"
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = "ERROR"
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, status in results.items():
        status_emoji = "✅" if status == "PASSED" else "❌"
        print(f"{status_emoji} {test_name}: {status}")
    
    passed = sum(1 for status in results.values() if status == "PASSED")
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The pipeline is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")

        print("\n📋 Troubleshooting Tips:")
       
       if results.get("Neo4j Connection") != "PASSED":
           print("  - Neo4j: Make sure Neo4j is running with 'docker-compose up -d'")
           print("           Check logs with 'docker-compose logs neo4j'")
       
       if results.get("Content Analysis (LLM)") != "PASSED":
           print("  - LLM: Ensure your ANTHROPIC_API_KEY is set in .env file")
           print("         Check with: echo $ANTHROPIC_API_KEY")
       
       if results.get("Knowledge Graph Node") != "PASSED":
           print("  - KG: Verify Neo4j is accessible at http://localhost:7474")
           print("        Login: neo4j / smartnotes123")


if __name__ == "__main__":
    main()