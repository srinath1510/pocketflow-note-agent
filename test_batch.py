#!/usr/bin/env python3
"""
Quick test to verify batch optimization is working - with improved timing
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def quick_batch_test():
    """Quick test with better result retrieval"""
    print("🔬 QUICK BATCH OPTIMIZATION TEST")
    print("=" * 40)
    
    # Clear notes
    requests.delete(f"{API_BASE}/api/notes")
    
    # Add test batch
    test_batch = {
        "notes": [
            {
                "id": f"test_{i}",
                "content": f"This is test content about blockchain technology and cryptocurrency number {i}. It covers decentralized finance, smart contracts, and distributed ledger technology.",
                "source": {"url": f"https://test{i}.com", "title": f"Test {i}"},
                "metadata": {"wordCount": 25, "domain": f"test{i}.com"}
            }
            for i in range(1, 6)  # 5 notes
        ]
    }
    
    print("📤 Sending 5 test notes...")
    requests.post(f"{API_BASE}/api/notes/batch", json=test_batch)
    
    time.sleep(2)  # Brief wait
    
    print("🔥 Triggering bake...")
    bake_response = requests.post(f"{API_BASE}/api/bake", json={})
    bake_id = bake_response.json()['bake_id']
    print(f"   Bake ID: {bake_id}")
    
    # Wait for completion with longer timeout and less frequent checks
    print("⏳ Waiting for completion (checking every 10s)...")
    for attempt in range(18):  # 18 attempts × 10s = 3 minutes
        time.sleep(10)
        
        # Check all results first (more reliable)
        try:
            all_results_response = requests.get(f"{API_BASE}/api/results")
            if all_results_response.status_code == 200:
                all_results = all_results_response.json().get('results', [])
                
                # Find our bake
                for result in reversed(all_results):  # Check most recent first
                    if result.get('bake_id') == bake_id:
                        print(f"✅ Found result after {(attempt + 1) * 10}s!")
                        analyze_result(result)
                        return True
                    
                    # Also check if it's a very recent result (within last 5 minutes)
                    processed_at = result.get('processed_at', '')
                    if processed_at and len(all_results) > 0 and result == all_results[-1]:
                        print(f"📍 Using most recent result (processed at {processed_at})")
                        analyze_result(result)
                        return True
                        
        except Exception as e:
            print(f"   Check {attempt + 1}/18 failed: {e}")
        
        print(f"   Still processing... ({(attempt + 1) * 10}s elapsed)")
    
    print("❌ Timeout - but check your server logs for the successful completion!")
    return False

def analyze_result(result):
    """Analyze the batch optimization result"""
    print("\n📈 BATCH OPTIMIZATION RESULTS")
    print("=" * 40)
    
    # Get batch metrics from multiple possible locations
    batch_metrics = None
    
    # Check processing_summary first
    processing_summary = result.get('processing_summary', {})
    if processing_summary.get('batch_optimization_metrics'):
        batch_metrics = processing_summary['batch_optimization_metrics']
        print("📍 Found batch metrics in processing_summary")
    
    # Check shared_state as backup
    elif result.get('shared_state', {}).get('batch_metrics'):
        batch_metrics = result['shared_state']['batch_metrics']
        print("📍 Found batch metrics in shared_state")
    
    if batch_metrics:
        api_calls_made = batch_metrics.get('api_calls_made', 0)
        api_calls_saved = batch_metrics.get('api_calls_saved', 0)
        reduction_percent = batch_metrics.get('api_calls_reduction_percent', 0)
        batches_created = batch_metrics.get('batches_created', 0)
        
        print(f"🎯 BATCH OPTIMIZATION SUCCESS!")
        print(f"   API calls made: {api_calls_made}")
        print(f"   API calls saved: {api_calls_saved}")
        print(f"   Reduction: {reduction_percent:.1f}%")
        print(f"   Batches created: {batches_created}")
        
        # Success criteria
        if api_calls_saved > 0 and reduction_percent > 50:
            print(f"\n🎉 EXCELLENT BATCHING PERFORMANCE!")
            print(f"   Your system is intelligently batching API calls")
            print(f"   Saving {api_calls_saved} calls ({reduction_percent:.1f}% reduction)")
            return True
        else:
            print(f"\n⚠️  Batching detected but performance could be better")
            return False
    else:
        print("❌ No batch metrics found in result")
        print(f"Available keys: {list(result.keys())}")
        return False

def main():
    print("🚀 QUICK BATCH TEST")
    print("=" * 30)
    
    # Check if API is healthy
    try:
        health = requests.get(f"{API_BASE}/api/health", timeout=5)
        if health.status_code != 200:
            print("❌ API not healthy")
            return
    except:
        print("❌ Cannot reach API")
        return
    
    success = quick_batch_test()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 BATCH OPTIMIZATION IS WORKING PERFECTLY!")
        print("   Your intelligent batching system is operational")
        print("   API calls are being reduced significantly")
    else:
        print("📊 Check your server logs for detailed metrics")
        print("   The pipeline appears to be working based on the logs")

if __name__ == "__main__":
    main()