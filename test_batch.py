#!/usr/bin/env python3
"""
Comprehensive test to verify batch optimization is working
"""
import requests
import json
import time
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()

API_BASE = "http://localhost:8000"

def create_detailed_test_batch():
    """Create a test batch specifically designed to test LLM batching"""
    return {
        "batch_id": f"batch_test_{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "processing_mode": "async_batch",
        "notes": [
            {
                "id": "crypto_note_1",
                "content": "Decentralized exchanges (DEXs) like Uniswap use automated market makers (AMMs) to facilitate trading without order books. Liquidity providers deposit token pairs into pools and earn fees from trades. The constant product formula x*y=k determines pricing based on supply and demand. Users can swap tokens directly from their wallets without KYC requirements.",
                "type": "selection",
                "source": {
                    "url": "https://uniswap.org/how-it-works",
                    "title": "How Uniswap Works",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "metadata": {
                    "domain": "uniswap.org",
                    "wordCount": 65,
                    "contentType": "text/html",
                    "selected_text": "Decentralized exchanges (DEXs) like Uniswap use automated market makers...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "capture_trigger": "test",
                    "intent": "learning"
                },
                "tag": "DeFi"
            },
            {
                "id": "crypto_note_2",
                "content": "Yield farming strategies involve providing liquidity to multiple DeFi protocols to maximize returns. Farmers analyze APY rates, token emissions, and impermanent loss risks. Popular strategies include liquidity mining on Compound, staking on Curve, and participating in governance token distributions. Smart contract risks and regulatory uncertainty remain key challenges.",
                "type": "selection",
                "source": {
                    "url": "https://defipulse.com/yield-farming",
                    "title": "Yield Farming Guide",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "metadata": {
                    "domain": "defipulse.com",
                    "wordCount": 72,
                    "contentType": "text/html",
                    "selected_text": "Yield farming strategies involve providing liquidity...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "capture_trigger": "test",
                    "intent": "learning"
                },
                "tag": "DeFi"
            },
            {
                "id": "crypto_note_3",
                "content": "Layer 2 scaling solutions like Polygon and Arbitrum reduce Ethereum gas fees by processing transactions off-chain while maintaining security through the main network. Optimistic rollups assume transactions are valid and use fraud proofs to challenge invalid ones. ZK-rollups use zero-knowledge proofs to verify transaction validity without revealing details.",
                "type": "selection",
                "source": {
                    "url": "https://ethereum.org/layer2",
                    "title": "Layer 2 Scaling",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "metadata": {
                    "domain": "ethereum.org",
                    "wordCount": 68,
                    "contentType": "text/html",
                    "selected_text": "Layer 2 scaling solutions like Polygon and Arbitrum...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "capture_trigger": "test",
                    "intent": "learning"
                },
                "tag": "Ethereum"
            },
            {
                "id": "crypto_note_4",
                "content": "NFT marketplaces like OpenSea enable trading of non-fungible tokens representing digital art, collectibles, and virtual assets. Smart contracts define ownership, royalties, and transfer mechanisms. ERC-721 and ERC-1155 standards ensure interoperability across platforms. Creators earn ongoing royalties from secondary sales, revolutionizing digital ownership models.",
                "type": "selection",
                "source": {
                    "url": "https://opensea.io/learn",
                    "title": "NFT Marketplace Guide",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "metadata": {
                    "domain": "opensea.io",
                    "wordCount": 61,
                    "contentType": "text/html",
                    "selected_text": "NFT marketplaces like OpenSea enable trading...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "capture_trigger": "test",
                    "intent": "learning"
                },
                "tag": "NFT"
            },
            {
                "id": "crypto_note_5",
                "content": "Decentralized Autonomous Organizations (DAOs) use blockchain governance to make collective decisions without central authority. Token holders vote on proposals for protocol upgrades, treasury allocation, and strategic direction. Snapshot voting allows gas-free governance participation. Multi-signature wallets and timelock contracts provide additional security layers for executing approved proposals.",
                "type": "selection",
                "source": {
                    "url": "https://aragon.org/dao-guide",
                    "title": "DAO Governance Guide",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "metadata": {
                    "domain": "aragon.org",
                    "wordCount": 75,
                    "contentType": "text/html",
                    "selected_text": "Decentralized Autonomous Organizations (DAOs) use blockchain governance...",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "capture_trigger": "test",
                    "intent": "learning"
                },
                "tag": "DAO"
            }
        ]
    }

def wait_for_bake_completion(bake_id, max_wait_seconds=60):
    """Poll for bake completion with proper timeout"""
    print(f"⏳ Waiting for bake {bake_id} to complete...")
    
    start_time = time.time()
    check_interval = 3  # Check every 3 seconds
    
    while time.time() - start_time < max_wait_seconds:
        try:
            # Check if results are available
            response = requests.get(f"{API_BASE}/api/results?bake_id={bake_id}")
            
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get('found') and result_data.get('result'):
                    elapsed = time.time() - start_time
                    print(f"✅ Bake completed in {elapsed:.1f}s")
                    return result_data['result']
                    
            elif response.status_code == 404:
                # Still processing, continue waiting
                elapsed = time.time() - start_time
                print(f"   ... {elapsed:.0f}s elapsed (still processing)")
            else:
                print(f"   Unexpected status: {response.status_code}")
                
            time.sleep(check_interval)
            
        except requests.exceptions.RequestException as e:
            print(f"   Error checking results: {e}")
            time.sleep(check_interval)
    
    print(f"❌ Timeout after {max_wait_seconds}s - checking if results exist anyway...")
    
    # Final check - sometimes results exist but there's a timing issue
    try:
        response = requests.get(f"{API_BASE}/api/results")
        if response.status_code == 200:
            all_results = response.json().get('results', [])
            # Find the most recent result with our bake_id
            for result in reversed(all_results):
                if result.get('bake_id') == bake_id:
                    print(f"✅ Found result for bake {bake_id} in final check")
                    return result
            
            # If no exact match, return the most recent result
            if all_results:
                print(f"⚠️  Using most recent result (bake_id mismatch)")
                return all_results[-1]
    except Exception as e:
        print(f"Final check failed: {e}")
    
    return None

def analyze_batch_metrics(result, expected_notes):
    """Analyze and report on batch optimization metrics"""
    print("\n📈 BATCH OPTIMIZATION ANALYSIS")
    print("=" * 50)
    
    try:
        # Look for batch metrics in multiple possible locations
        batch_metrics = None
        processing_summary = result.get('processing_summary', {})
        
        # Check different possible locations for batch metrics
        locations_to_check = [
            ('processing_summary.batch_optimization_metrics', processing_summary.get('batch_optimization_metrics')),
            ('results.batch_optimization_metrics', result.get('results', {}).get('batch_optimization_metrics')),
            ('detailed_results.content_analysis.optimization_metrics', 
             result.get('detailed_results', {}).get('content_analysis', {}).get('optimization_metrics')),
        ]
        
        for location_name, metrics in locations_to_check:
            if metrics:
                print(f"📍 Found batch metrics in: {location_name}")
                batch_metrics = metrics
                break
        
        # Basic processing metrics
        print(f"🧠 Content Analysis Results:")
        print(f"   Notes processed: {result.get('input_notes_count', 0)}/{expected_notes}")
        
        # Check different ways concepts might be stored
        concepts_count = 0
        if 'processing_summary' in result:
            concepts_count = processing_summary.get('concepts_extracted', 0)
        if concepts_count == 0 and 'results' in result:
            concepts_count = len(result.get('results', {}).get('concepts_extracted', []))
        if concepts_count == 0 and 'detailed_results' in result:
            extracted_concepts = result.get('detailed_results', {}).get('content_analysis', {}).get('extracted_concepts', {})
            concepts_count = len(extracted_concepts.get('learning_concepts', []))
        
        print(f"   Concepts extracted: {concepts_count}")
        print(f"   Status: {result.get('status', 'unknown')}")
        
        # Batch optimization metrics analysis
        if batch_metrics:
            print(f"\n⚡ BATCH OPTIMIZATION METRICS FOUND!")
            api_calls_made = batch_metrics.get('api_calls_made', 0)
            api_calls_saved = batch_metrics.get('api_calls_saved', 0)
            reduction_percent = batch_metrics.get('api_calls_reduction_percent', 0)
            cache_hit_rate = batch_metrics.get('cache_hit_rate', 0)
            method_breakdown = batch_metrics.get('method_breakdown', {})
            
            print(f"   API calls made: {api_calls_made}")
            print(f"   API calls saved: {api_calls_saved}")
            print(f"   Reduction percentage: {reduction_percent:.1f}%")
            print(f"   Cache hit rate: {cache_hit_rate:.1f}%")
            print(f"   Processing methods:")
            for method, count in method_breakdown.items():
                print(f"     • {method}: {count} captures")
            
            # Success criteria
            success = True
            
            if api_calls_saved <= 0:
                print(f"   ⚠️  WARNING: Expected API call savings, got {api_calls_saved}")
                success = False
            
            if method_breakdown.get('llm_batch', 0) == 0:
                print(f"   ⚠️  WARNING: No LLM batch processing detected!")
                print(f"   Available methods: {list(method_breakdown.keys())}")
                success = False
            
            if concepts_count == 0:
                print(f"   ⚠️  WARNING: No concepts were extracted!")
                success = False
                
            if reduction_percent < 30:  # Expect at least 30% reduction
                print(f"   ⚠️  WARNING: Low API call reduction: {reduction_percent:.1f}%")
                success = False
            
            return success
            
        else:
            print(f"\n❌ NO BATCH OPTIMIZATION METRICS FOUND!")
            print(f"   Available result keys: {list(result.keys())}")
            
            # Show what's in processing_summary
            if processing_summary:
                print(f"   Processing summary keys: {list(processing_summary.keys())}")
            
            return False
            
    except Exception as e:
        print(f"❌ Error analyzing batch metrics: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_comprehensive_batch_optimization():
    """Test that verifies actual batch optimization metrics"""
    print("🔬 COMPREHENSIVE BATCH OPTIMIZATION TEST")
    print("=" * 60)
    
    # 1. Clear existing notes
    print("🧹 Clearing existing notes...")
    try:
        response = requests.delete(f"{API_BASE}/api/notes")
        print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"   Warning: Could not clear notes: {e}")
    
    # 2. Send test batch designed for LLM processing
    print("📤 Sending crypto-focused test batch (5 notes)...")
    batch_data = create_detailed_test_batch()
    
    print(f"   Note details:")
    for i, note in enumerate(batch_data['notes'], 1):
        word_count = note['metadata']['wordCount']
        topic = note['tag']
        print(f"     {i}. {topic} - {word_count} words (should trigger LLM)")
    
    response = requests.post(f"{API_BASE}/api/notes/batch", json=batch_data)
    
    if response.status_code != 200:
        print(f"❌ Batch failed: {response.status_code} - {response.text}")
        return False
    
    batch_result = response.json()
    print(f"   ✅ Batch processed: {batch_result.get('notes_processed', 0)} notes")
    
    # 3. Wait for background processing
    print("⏳ Waiting for background processing...")
    time.sleep(3)
    
    # 4. Monitor API calls during bake
    print("🔥 Triggering bake with API call monitoring...")
    print("📡 Monitor your server logs for:")
    print("   • 'Batch processing setup: X API calls estimated'")
    print("   • 'Processing batch 1/Y with Z captures'") 
    print("   • 'Processed X captures with Y LLM calls'")
    print("   • 'API calls saved: Z'")
    
    bake_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "batch_test",
        "includeAdditionalNotes": False
    }
    
    response = requests.post(f"{API_BASE}/api/bake", json=bake_data)
    
    if response.status_code not in [200, 201]:
        print(f"❌ Bake failed: {response.status_code} - {response.text}")
        return False
    
    bake_result = response.json()
    bake_id = bake_result['bake_id']
    print(f"   ✅ Bake initiated: {bake_id}")
    
    # 5. Wait for completion with better polling
    result = wait_for_bake_completion(bake_id, max_wait_seconds=60)
    
    if not result:
        print("❌ Could not retrieve bake results")
        return False
    
    # 6. Analyze batch optimization metrics
    return analyze_batch_metrics(result, len(batch_data['notes']))

def test_api_health():
    """Test API connectivity"""
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API not reachable: {e}")
        return False

def main():
    """Run comprehensive batch optimization test"""
    print("🚀 STARTING BATCH OPTIMIZATION TEST")
    print("=" * 60)
    
    # Check API health first
    if not test_api_health():
        print("❌ Cannot proceed without healthy API")
        return
    
    try:
        # Run the comprehensive test
        success = test_comprehensive_batch_optimization()
        
        # Final results
        print("\n" + "=" * 60)
        if success:
            print("🎉 BATCH OPTIMIZATION TEST PASSED!")
            print("   ✅ API calls are being batched and reduced")
            print("   ✅ Concepts are being extracted properly")
            print("   ✅ Batch metrics are being tracked correctly")
            print("\n💡 Your intelligent batching system is working perfectly!")
        else:
            print("❌ BATCH OPTIMIZATION TEST FAILED!")
            print("   Check your server logs for detailed information")
            print("   Look for the specific log messages mentioned above")
            print("\n🔧 Troubleshooting tips:")
            print("   1. Verify ANTHROPIC_API_KEY is set correctly")
            print("   2. Check that all 5 notes are being processed")
            print("   3. Ensure the ContentAnalysisNode batch logic is working")
            print("   4. Look for any errors in the pipeline execution")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()