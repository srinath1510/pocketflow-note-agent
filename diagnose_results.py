#!/usr/bin/env python3
"""
Diagnostic script to check what's happening with results storage
"""
import requests
import json

API_BASE = "http://localhost:8000"

def diagnose_results():
    """Check all possible result locations"""
    print("🔍 RESULTS DIAGNOSTIC")
    print("=" * 40)
    
    # 1. Check all results endpoint
    print("1️⃣ Checking /api/results (all results)...")
    try:
        response = requests.get(f"{API_BASE}/api/results")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Total results: {data.get('total_results', 0)}")
            
            results = data.get('results', [])
            if results:
                print(f"   Available results:")
                for i, result in enumerate(results):
                    bake_id = result.get('bake_id', 'unknown')
                    status = result.get('status', 'unknown')
                    print(f"     {i+1}. Bake ID: {bake_id}, Status: {status}")
                
                # Show structure of most recent result
                latest = results[-1]
                print(f"\n   📋 Latest result structure:")
                print(f"     Keys: {list(latest.keys())}")
                
                # Check for batch metrics in different locations
                processing_summary = latest.get('processing_summary', {})
                if processing_summary:
                    print(f"     Processing summary keys: {list(processing_summary.keys())}")
                    
                    batch_metrics = processing_summary.get('batch_optimization_metrics')
                    if batch_metrics:
                        print(f"     ✅ Found batch metrics in processing_summary!")
                        print(f"        API calls made: {batch_metrics.get('api_calls_made', 'unknown')}")
                        print(f"        API calls saved: {batch_metrics.get('api_calls_saved', 'unknown')}")
                    else:
                        print(f"     ❌ No batch_optimization_metrics in processing_summary")
                
                # Check detailed_results
                detailed_results = latest.get('detailed_results', {})
                if detailed_results:
                    print(f"     Detailed results keys: {list(detailed_results.keys())}")
                    
                    content_analysis = detailed_results.get('content_analysis', {})
                    if content_analysis:
                        print(f"     Content analysis keys: {list(content_analysis.keys())}")
                        
                        opt_metrics = content_analysis.get('optimization_metrics')
                        if opt_metrics:
                            print(f"     ✅ Found optimization metrics in detailed_results!")
                        else:
                            print(f"     ❌ No optimization_metrics in content_analysis")
            else:
                print("   ❌ No results found in response")
        else:
            print(f"   ❌ Failed to get results: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. Check specific bake ID
    print("\n2️⃣ Checking specific bake ID...")
    bake_id = "781af03b-ba12-4c87-827c-73f01e0aac43"  # From your test
    
    try:
        response = requests.get(f"{API_BASE}/api/results?bake_id={bake_id}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Found: {data.get('found', False)}")
            print(f"   Source: {data.get('source', 'unknown')}")
            
            if data.get('found'):
                result = data.get('result', {})
                print(f"   Result keys: {list(result.keys())}")
            else:
                print(f"   Message: {data.get('message', 'No message')}")
        else:
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Check files on disk
    print("\n3️⃣ Checking result files...")
    import os
    from pathlib import Path
    
    results_dir = Path("data/results")
    if results_dir.exists():
        files = list(results_dir.glob(f"*{bake_id}*"))
        print(f"   Files found: {len(files)}")
        
        for file in files:
            print(f"     📄 {file.name}")
            try:
                with open(file, 'r') as f:
                    file_data = json.load(f)
                    print(f"        Keys: {list(file_data.keys())}")
                    
                    # Check for batch metrics
                    if 'processing_summary' in file_data:
                        ps = file_data['processing_summary']
                        if 'batch_optimization_metrics' in ps:
                            print(f"        ✅ Has batch metrics!")
                        else:
                            print(f"        ❌ No batch metrics")
            except Exception as fe:
                print(f"        ❌ Error reading file: {fe}")
    else:
        print(f"   ❌ Results directory doesn't exist")

def test_simple_bake():
    """Run a simple bake to see what happens"""
    print("\n🧪 SIMPLE BAKE TEST")
    print("=" * 30)
    
    # Clear notes
    print("   Clearing notes...")
    requests.delete(f"{API_BASE}/api/notes")
    
    # Add one simple note
    print("   Adding test note...")
    simple_batch = {
        "notes": [{
            "id": "test_note_1",
            "content": "This is a simple test note about artificial intelligence and machine learning concepts for testing batch optimization.",
            "source": {"url": "https://test.com", "title": "Test"},
            "metadata": {"wordCount": 20, "domain": "test.com"}
        }]
    }
    
    response = requests.post(f"{API_BASE}/api/notes/batch", json=simple_batch)
    if response.status_code == 200:
        print("   ✅ Note added")
        
        # Wait a moment
        import time
        time.sleep(2)
        
        # Trigger bake
        print("   Triggering bake...")
        bake_response = requests.post(f"{API_BASE}/api/bake", json={})
        
        if bake_response.status_code == 200:
            bake_data = bake_response.json()
            test_bake_id = bake_data['bake_id']
            print(f"   ✅ Bake started: {test_bake_id}")
            
            # Wait for completion
            print("   Waiting 30 seconds...")
            time.sleep(30)
            
            # Check results
            result_response = requests.get(f"{API_BASE}/api/results?bake_id={test_bake_id}")
            print(f"   Result status: {result_response.status_code}")
            
            if result_response.status_code == 200:
                result_data = result_response.json()
                print(f"   Found: {result_data.get('found', False)}")
                print(f"   Source: {result_data.get('source', 'unknown')}")
            
        else:
            print(f"   ❌ Bake failed: {bake_response.status_code}")
    else:
        print(f"   ❌ Note add failed: {response.status_code}")

def main():
    """Run diagnostic"""
    diagnose_results()
    test_simple_bake()

if __name__ == "__main__":
    main()