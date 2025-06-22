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


def test_full_pipeline_preview():
    """Test the full pipeline (currently only has capture ingestion)."""
    print("\nTesting Full Pipeline (Current Implementation)")
    print("=" * 50)
    
    # Simple test data
    test_data = {
        "url": "https://example.com/test-article",
        "content": """<html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Test Article</h1>
            <p>This is a test article for the pipeline.</p>
            <h2>Features</h2>
            <ul>
                <li>Simple content</li>
                <li>Basic structure</li>
            </ul>
        </body>
        </html>""",
        "timestamp": "2025-06-16T12:00:00Z",
        "selected_text": "test article",
        "highlights": ["test article"],
        "dwell_time": 30000,
        "scroll_depth": 0.5,
        "trigger": "test",
        "intent": "testing"
    }
    
    # Initialize pipeline
    pipeline = NoteGenerationPipeline()
    
    try:
        # Run the full pipeline (currently only capture ingestion)
        result = pipeline.run(test_data)
        
        print(f"✅ Full pipeline completed!")
        print(f"Session ID: {result['session_id']}")
        print(f"Pipeline Stage: {result.get('pipeline_stage', 'unknown')}")
        
        # Display pipeline metadata
        if "pipeline_metadata" in result:
            metadata = result["pipeline_metadata"]
            print(f"\nPipeline Metadata:")
            print(f"  Status: {metadata.get('status', 'unknown')}")
            print(f"  Start Time: {metadata.get('start_time', 'unknown')}")
            print(f"  End Time: {metadata.get('end_time', 'unknown')}")
            print(f"  Config Version: {metadata.get('config_version', 'unknown')}")
            print(f"  Pipeline Version: {metadata.get('pipeline_version', 'unknown')}")
        
        # Display captured data
        if "raw_captures" in result:
            captures = result["raw_captures"]
            print(f"\nCaptured Data:")
            print(f"  Processed Captures: {len(captures)}")
            
            for capture in captures:
                print(f"  📄 {capture['metadata']['page_title']}")
                print(f"     Category: {capture['metadata']['content_category']}")
                print(f"     Words: {capture['metadata']['word_count']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Full pipeline test failed: {str(e)}")
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
    
    tests = [
        ("Single Capture", test_capture_ingestion_single),
        ("Batch Processing", test_capture_ingestion_batch),
        ("Invalid Data Handling", test_invalid_data),
        ("Full Pipeline Preview", test_full_pipeline_preview)
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
        print("🎉 All tests passed! The Capture Ingestion node is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()