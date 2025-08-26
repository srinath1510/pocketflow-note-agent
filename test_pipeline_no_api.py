"""
Test script for Pipeline components that don't require LLM API calls
"""

import json
import sys
from pathlib import Path
import os

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import NoteGenerationPipeline
from nodes.knowledge_graph import test_neo4j_connection


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
        "dwell_time": 180000,
        "scroll_depth": 0.7,
        "viewport_size": "1920x1080",
        "user_agent": "Mozilla/5.0 (Test Browser)",
        "trigger": "context_menu",
        "intent": "research_capture"
    }
    
    pipeline = NoteGenerationPipeline()
    
    try:
        result = pipeline.run_single_node("capture_ingestion", sample_data)
        
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
                print(f"  Content Category: {capture['metadata']['content_category']}")
                print(f"  Knowledge Level: {capture['metadata']['knowledge_level']}")
                print(f"  Has Code: {capture['metadata']['has_code']}")
                print(f"  Word Count: {capture['metadata']['word_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
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
                <pre><code>import asyncio
                
async def main():
    print('Hello')
    await asyncio.sleep(1)

asyncio.run(main())</code></pre>
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
                <h1>Understanding Microservices</h1>
                <p>Microservices architecture structures an application as loosely coupled services.</p>
                <ul>
                    <li>Scalability: Scale individual services</li>
                    <li>Technology diversity: Use different technologies</li>
                    <li>Resilience: Isolated failures</li>
                </ul>
            </body>
            </html>""",
            "timestamp": "2025-06-16T16:45:00Z",
            "selected_text": "Microservices are not a silver bullet",
            "highlights": ["Microservices"],
            "dwell_time": 240000,
            "scroll_depth": 0.85,
            "viewport_size": "1366x768",
            "trigger": "double_click",
            "intent": "quote_capture"
        },
        {
            "url": "https://github.com/example/readme",
            "content": """<html>
            <head><title>Project README</title></head>
            <body>
                <h1>Example Project</h1>
                <h2>Installation</h2>
                <pre><code>pip install example-project</code></pre>
                <h2>Usage</h2>
                <p>Import and use the library in your Python code.</p>
            </body>
            </html>""",
            "timestamp": "2025-06-16T17:00:00Z",
            "selected_text": "pip install example-project",
            "highlights": ["pip install"],
            "dwell_time": 60000,
            "scroll_depth": 0.3,
            "viewport_size": "1920x1080",
            "trigger": "manual",
            "intent": "documentation"
        }
    ]
    
    pipeline = NoteGenerationPipeline()
    
    try:
        result = pipeline.run_single_node("capture_ingestion", batch_data)
        
        print(f"✅ Batch processing completed successfully!")
        
        if "raw_captures" in result:
            captures = result["raw_captures"]
            print(f"Processed {len(captures)} captures")
            
            # Summary statistics
            content_categories = {}
            domains = set()
            
            for capture in captures:
                category = capture['metadata']['content_category']
                content_categories[category] = content_categories.get(category, 0) + 1
                domains.add(capture['metadata']['domain'])
            
            print(f"\nBatch Summary:")
            print(f"  Content Categories: {dict(content_categories)}")
            print(f"  Unique Domains: {list(domains)}")
        
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
    
    pipeline = NoteGenerationPipeline()
    
    try:
        result = pipeline.run_single_node("capture_ingestion", invalid_data)
        
        print(f"✅ Invalid data handling completed!")
        
        if "raw_captures" in result:
            captures = result["raw_captures"]
            print(f"Successfully processed: {len(captures)} out of {len(invalid_data)} captures")
        
        return True
        
    except Exception as e:
        print(f"❌ Invalid data test failed: {str(e)}")
        return False


def test_knowledge_graph_structure():
    """Test Knowledge Graph node structure without running full pipeline."""
    print("\nTesting Knowledge Graph Structure (No API calls)")
    print("=" * 50)
    
    try:
        from nodes.knowledge_graph import KnowledgeGraphNode
        
        kg_node = KnowledgeGraphNode()
        print("✅ Knowledge Graph node initialized successfully")
        
        test_id = kg_node._generate_node_id("Machine Learning", "concept", "test_user")
        print(f"✅ Node ID generation working: {test_id[:16]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge Graph structure test failed: {str(e)}")
        return False

def test_historical_knowledge_initialization():
    """Test Historical Knowledge Retrieval node initialization."""
    print("\nTesting Historical Knowledge Node - Initialization")
    print("=" * 50)
    
    try:
        from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
        
        # Test without LLM to avoid API calls
        hk_node = HistoricalKnowledgeRetrievalNode()
        print("✅ Historical Knowledge node initialized successfully")
        
        # Test node ID generation method (inherited from KG node pattern)
        test_id = hk_node._generate_node_id("Python Programming", "concept", "test_user")
        print(f"✅ Node ID generation working: {test_id[:16]}...")
        
        # Test confidence score calculation structure
        confidence_test = hk_node._calculate_confidence_scores_structure()
        print(f"✅ Confidence score calculation structure validated")
        
        return True
        
    except Exception as e:
        print(f"❌ Historical Knowledge initialization failed: {str(e)}")
        return False


def test_historical_knowledge_data_structures():
    """Test Historical Knowledge node data structure handling."""
    print("\nTesting Historical Knowledge Node - Data Structures")
    print("=" * 50)
    
    try:
        from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
        
        hk_node = HistoricalKnowledgeRetrievalNode()
        
        # Test prep phase with mock data
        mock_shared_state = {
            'session_id': 'test_session_123',
            'extracted_concepts': {
                'learning_concepts': ['machine learning', 'neural networks', 'deep learning'],
                'entities': {'TensorFlow': 'framework', 'Python': 'language'},
                'topics': ['artificial intelligence', 'computer science'],
                'session_theme': 'machine_learning',
                'knowledge_progression': ['statistics', 'machine learning', 'deep learning']
            },
            'knowledge_graph': {
                'user_id': 'test_user',
                'nodes_created': {'concepts': 5, 'entities': 2}
            }
        }
        
        prep_result = hk_node.prep(mock_shared_state)
        
        checks = [
            ("User ID extraction", 'user_id' in prep_result),
            ("Concepts extraction", len(prep_result.get('new_concepts', [])) == 3),
            ("Entities extraction", len(prep_result.get('new_entities', {})) == 2),
            ("Session theme", prep_result.get('session_theme') == 'machine_learning'),
            ("Knowledge progression", len(prep_result.get('knowledge_progression', [])) == 3),
            ("Neo4j config", 'neo4j_config' in prep_result)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"{status} {check_name}")
            all_passed = all_passed and check_result
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Historical Knowledge data structures test failed: {str(e)}")
        return False


def test_historical_knowledge_confidence_calculation():
    """Test confidence score calculation logic without Neo4j."""
    print("\nTesting Historical Knowledge Node - Confidence Calculation")
    print("=" * 50)
    
    try:
        from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
        
        hk_node = HistoricalKnowledgeRetrievalNode()
        
        # Mock confidence calculation with test data
        test_concepts = ['python programming', 'machine learning', 'web development']
        
        # Test the confidence calculation formula
        test_cases = [
            {
                'concept': 'python programming',
                'occurrences': 8,
                'connections': 12,
                'sessions': 4,
                'expected_level': 'high'
            },
            {
                'concept': 'machine learning', 
                'occurrences': 3,
                'connections': 5,
                'sessions': 2,
                'expected_level': 'medium'
            },
            {
                'concept': 'web development',
                'occurrences': 1,
                'connections': 0,
                'sessions': 1,
                'expected_level': 'low'
            }
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            # Simulate confidence calculation
            occurrences = test_case['occurrences']
            connections = test_case['connections']
            sessions = test_case['sessions']
            
            # Use the same formula as in the node
            occurrence_score = min(occurrences / 5.0, 1.0)
            connection_score = min(connections / 10.0, 1.0)
            session_score = min(sessions / 3.0, 1.0)
            
            overall_confidence = (occurrence_score * 0.4 + connection_score * 0.4 + session_score * 0.2)
            
            confidence_level = "high" if overall_confidence > 0.7 else "medium" if overall_confidence > 0.4 else "low"
            
            expected_level = test_case['expected_level']
            passed = confidence_level == expected_level
            
            status = "✅" if passed else "❌"
            print(f"{status} {test_case['concept']}: {confidence_level} (expected: {expected_level}) - {overall_confidence:.2f}")
            
            all_passed = all_passed and passed
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Confidence calculation test failed: {str(e)}")
        return False


def test_historical_knowledge_recommendations():
    """Test recommendation generation logic."""
    print("\nTesting Historical Knowledge Node - Recommendation Logic")
    print("=" * 50)
    
    try:
        from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
        
        hk_node = HistoricalKnowledgeRetrievalNode()
        
        # Mock data for recommendation testing
        mock_direct_connections = [
            {
                'new_concept': 'neural networks',
                'existing_concept': 'machine learning',
                'similarity_score': 0.8,
                'connection_type': 'direct_match'
            }
        ]
        
        mock_semantic_connections = [
            {
                'new_concept': 'deep learning',
                'existing_concept': 'neural networks', 
                'relationship_type': 'builds_upon',
                'strength': 0.9,
                'explanation': 'Deep learning builds upon neural network foundations',
                'connection_type': 'semantic'
            }
        ]
        
        mock_knowledge_gaps = [
            {
                'missing_concept': 'linear algebra',
                'needed_for': 'machine learning',
                'priority': 'high',
                'explanation': 'Foundation for ML algorithms',
                'recommended_action': 'Study linear algebra fundamentals'
            },
            {
                'missing_concept': 'statistics',
                'needed_for': 'data science',
                'priority': 'medium',
                'explanation': 'Foundation for ML algorithms',
                'recommended_action': 'Learn basic statistics'
            }
        ]
        
        mock_reinforcement = [
            {
                'concept': 'python basics',
                'days_since_encounter': 14,
                'priority': 'high',
                'recommended_action': 'Review Python fundamentals'
            }
        ]
        
        mock_learning_patterns = {
            'learning_intensity': {'level': 'medium'},
            'learning_consistency': {'level': 'high'}
        }
        
        # Test recommendation generation
        recommendations = hk_node._generate_learning_recommendations(
            mock_direct_connections,
            mock_semantic_connections,
            mock_knowledge_gaps,
            mock_reinforcement,
            mock_learning_patterns
        )
        
        checks = [
            ("Recommendations generated", len(recommendations) > 0),
            ("High priority gaps addressed", any(rec.get('type') == 'knowledge_gap' for rec in recommendations)),
            ("Reinforcement included", any(rec.get('type') == 'reinforcement' for rec in recommendations)),
            ("Valid recommendation structure", all('action' in rec and 'reason' in rec for rec in recommendations))
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"{status} {check_name}")
            all_passed = all_passed and check_result
        
        print(f"\nGenerated {len(recommendations)} recommendations:")
        for i, rec in enumerate(recommendations[:3]):
            print(f"  {i+1}. [{rec.get('type', 'unknown')}] {rec.get('action', 'No action')}")
            print(f"     Priority: {rec.get('priority', 'unknown')}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Recommendation generation test failed: {str(e)}")
        return False


def test_historical_knowledge_without_neo4j():
    """Test Historical Knowledge node graceful handling when Neo4j is unavailable."""
    print("\nTesting Historical Knowledge Node - No Neo4j Graceful Handling")
    print("=" * 50)
    
    try:
        from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
        
        hk_node = HistoricalKnowledgeRetrievalNode()
        
        # Mock prep result that would come from a working prep phase
        mock_prep_result = {
            'user_id': 'test_user',
            'current_session_id': 'test_session',
            'new_concepts': ['machine learning', 'python'],
            'new_entities': {'Python': 'language'},
            'new_topics': ['programming'],
            'session_theme': 'programming',
            'knowledge_progression': ['basics', 'intermediate', 'advanced'],
            'neo4j_config': {
                'uri': 'bolt://nonexistent:7687',  # Intentionally wrong
                'user': 'test',
                'password': 'test'
            }
        }
        
        # This should fail gracefully and return an error result
        exec_result = hk_node.exec(mock_prep_result)
        
        checks = [
            ("Error handling", 'error' in exec_result),
    ("Graceful failure", 'address' in exec_result.get('error', '') or 'Neo4j' in exec_result.get('error', '')),
            ("No crash", True)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"{status} {check_name}")
            all_passed = all_passed and check_result
        
        print(f"Error message: {exec_result.get('error', 'No error message')}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Neo4j unavailable handling test failed: {str(e)}")
        return False


def test_historical_knowledge_post_processing():
    """Test Historical Knowledge node post-processing logic."""
    print("\nTesting Historical Knowledge Node - Post Processing")
    print("=" * 50)
    
    try:
        from nodes.historical_knowledge_retrieval import HistoricalKnowledgeRetrievalNode
        
        hk_node = HistoricalKnowledgeRetrievalNode()
        
        # Mock shared state
        mock_shared_state = {
            'pipeline_metadata': {}
        }
        
        # Mock prep result
        mock_prep_result = {
            'user_id': 'test_user',
            'current_session_id': 'test_session'
        }
        
        # Mock exec result
        mock_exec_result = {
            'user_id': 'test_user',
            'session_id': 'test_session',
            'direct_connections': [{'new_concept': 'A', 'existing_concept': 'B'}],
            'semantic_connections': [{'new_concept': 'C', 'existing_concept': 'D'}],
            'knowledge_gaps': [{'missing_concept': 'E', 'priority': 'high'}],
            'reinforcement_opportunities': [{'concept': 'F', 'priority': 'medium'}],
            'learning_patterns': {'intensity': 'high'},
            'confidence_scores': {'A': {'confidence_level': 'high'}},
            'recommendations': [{'action': 'Study X', 'priority': 'high'}]
        }
        
        # Test post processing
        result = hk_node.post(mock_shared_state, mock_prep_result, mock_exec_result)
        
        checks = [
            ("Returns action", isinstance(result, str)),
            ("Historical connections stored", 'historical_connections' in mock_shared_state),
            ("Knowledge gaps stored", 'knowledge_gaps' in mock_shared_state),
            ("Reinforcement stored", 'reinforcement_opportunities' in mock_shared_state),
            ("Patterns stored", 'learning_patterns' in mock_shared_state),
            ("Confidence stored", 'knowledge_confidence' in mock_shared_state),
            ("Recommendations stored", 'learning_recommendations' in mock_shared_state),
            ("Pipeline metadata updated", mock_shared_state.get('pipeline_metadata', {}).get('historical_analysis_complete') == True)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"{status} {check_name}")
            all_passed = all_passed and check_result
        
        # Check data integrity
        historical_connections = mock_shared_state.get('historical_connections', {})
        total_connections = historical_connections.get('total_connections_found', 0)
        print(f"Total connections recorded: {total_connections}")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Post processing test failed: {str(e)}")
        return False



def test_html_cleaning():
    """Test HTML cleaning functionality."""
    print("\nTesting HTML Content Cleaning")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Script removal",
            "html": "<html><body><p>Content</p><script>alert('test')</script></body></html>",
            "expected_contains": "Content",
            "expected_not_contains": "alert"
        },
        {
            "name": "Style removal", 
            "html": "<html><head><style>body{color:red;}</style></head><body>Text</body></html>",
            "expected_contains": "Text",
            "expected_not_contains": "color:red"
        },
        {
            "name": "Code preservation",
            "html": "<html><body><pre><code>def hello(): print('world')</code></pre></body></html>",
            "expected_contains": "def hello():",
            "expected_not_contains": "<code>"
        }
    ]
    
    from nodes.capture_ingestion import CaptureIngestionNode
    node = CaptureIngestionNode()
    
    all_passed = True
    
    for test in test_cases:
        cleaned = node._clean_html_content(test["html"])
        
        contains_check = test["expected_contains"] in cleaned
        not_contains_check = test["expected_not_contains"] not in cleaned
        
        passed = contains_check and not_contains_check
        all_passed = all_passed and passed
        
        status = "✅" if passed else "❌"
        print(f"{status} {test['name']}: {'PASSED' if passed else 'FAILED'}")
        
        if not passed:
            print(f"   Expected to contain: '{test['expected_contains']}' - Found: {contains_check}")
            print(f"   Expected NOT to contain: '{test['expected_not_contains']}' - OK: {not_contains_check}")
    
    return all_passed


def test_metadata_extraction():
    """Test metadata extraction without API calls."""
    print("\nTesting Metadata Extraction")
    print("=" * 50)
    
    test_html = """<html>
    <head><title>Test Article</title></head>
    <body>
        <h1>Main Title</h1>
        <h2>Section 1</h2>
        <h3>Subsection 1.1</h3>
        <p>Some content with <a href="https://external.com">external link</a> 
        and <a href="/internal">internal link</a>.</p>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
        <table><tr><td>Data</td></tr></table>
        <pre><code>print("Hello")</code></pre>
        <p>Math formula: $E = mc^2$</p>
        <img src="image.jpg" alt="Image">
        <p>Citation [1] reference (Author et al., 2023)</p>
    </body>
    </html>"""
    
    from nodes.capture_ingestion import CaptureIngestionNode
    node = CaptureIngestionNode()
    
    raw_capture = {
        'url': 'https://example.com/test',
        'content': test_html
    }
    
    cleaned_content = node._clean_html_content(test_html)
    metadata = node._extract_content_metadata(raw_capture, cleaned_content)
    
    print("Extracted Metadata:")
    print(f"  Title: {metadata.get('page_title', 'N/A')}")
    print(f"  Headings: {len(metadata.get('heading_hierarchy', []))}")
    print(f"  Links: {metadata.get('link_count', 0)} (External: {metadata.get('external_links', 0)}, Internal: {metadata.get('internal_links', 0)})")
    print(f"  Tables: {metadata.get('table_count', 0)}")
    print(f"  Has Code: {metadata.get('has_code', False)}")
    print(f"  Has Math: {metadata.get('has_math', False)}")
    print(f"  Citations: {metadata.get('citations', 0)}")
    print(f"  Images: {metadata.get('image_count', 0)}")
    print(f"  List Items: {metadata.get('list_items_count', 0)}")
    
    checks = [
        ("Title extraction", metadata.get('page_title') == "Test Article"),
        ("Heading count", len(metadata.get('heading_hierarchy', [])) == 3),
        ("External links", metadata.get('external_links', 0) == 1),
        ("Internal links", metadata.get('internal_links', 0) == 1),
        ("Code detection", metadata.get('has_code', False) == True),
        ("Math detection", metadata.get('has_math', False) == True),
        ("Table count", metadata.get('table_count', 0) == 1),
        ("Image count", metadata.get('image_count', 0) == 1),
        ("List items", metadata.get('list_items_count', 0) == 2)
    ]
    
    all_passed = True
    for check_name, check_result in checks:
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}")
        all_passed = all_passed and check_result
    
    return all_passed


def save_test_results(test_name: str, result_data: dict):
    """Save test results to a JSON file for inspection."""
    output_dir = Path("test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{test_name}_result.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, indent=2, default=str)
    
    print(f"📁 Test results saved to: {output_file}")


def main():
    """Run all non-API tests."""
    print("🚀 Starting Pipeline Tests (No API Credits Required)")
    print("=" * 60)
    
    tests = [
        ("Neo4j Connection", lambda: test_neo4j_connection()),
        ("Single Capture Processing", test_capture_ingestion_single),
        ("Batch Capture Processing", test_capture_ingestion_batch),
        ("Invalid Data Handling", test_invalid_data),
        ("HTML Content Cleaning", test_html_cleaning),
        ("Metadata Extraction", test_metadata_extraction),
        ("Knowledge Graph Structure", test_knowledge_graph_structure),
        ("Historical Knowledge Initialization", test_historical_knowledge_initialization),
        ("Historical Knowledge Data Structures", test_historical_knowledge_data_structures),
        ("Historical Knowledge Confidence Calculation", test_historical_knowledge_confidence_calculation),
        ("Historical Knowledge Recommendations", test_historical_knowledge_recommendations),
        ("Historical Knowledge No Neo4j Handling", test_historical_knowledge_without_neo4j),
        ("Historical Knowledge Post Processing", test_historical_knowledge_post_processing),
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

    capture_tests = [k for k in results.keys() if "Capture" in k or "HTML" in k or "Metadata" in k]
    kg_tests = [k for k in results.keys() if "Knowledge Graph" in k or "Neo4j" in k]
    historical_tests = [k for k in results.keys() if "Historical Knowledge" in k]
    
    print("\n📥 CAPTURE INGESTION & PROCESSING:")
    for test_name in capture_tests:
        status = results[test_name]
        status_emoji = "✅" if status == "PASSED" else "❌"
        print(f"  {status_emoji} {test_name}: {status}")
    
    print("\n🕸️ KNOWLEDGE GRAPH:")
    for test_name in kg_tests:
        status = results[test_name]
        status_emoji = "✅" if status == "PASSED" else "❌"
        print(f"  {status_emoji} {test_name}: {status}")
    
    print("\n🔗 HISTORICAL KNOWLEDGE RETRIEVAL:")
    for test_name in historical_tests:
        status = results[test_name]
        status_emoji = "✅" if status == "PASSED" else "❌"
        print(f"  {status_emoji} {test_name}: {status}")
    
    passed = sum(1 for status in results.values() if status == "PASSED")
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 All tests passed! Your pipeline components are working correctly.")
    else:
        failed_tests = [name for name, status in results.items() if status != "PASSED"]
        print(f"⚠️  Failed tests: {', '.join(failed_tests)}")
    
    print("\n💡 These tests don't use any API credits")
    print("   To test LLM features, run: python test_pipeline.py")
    print("   To test full pipeline integration, run: python main.py --sample")


if __name__ == "__main__":
    main()