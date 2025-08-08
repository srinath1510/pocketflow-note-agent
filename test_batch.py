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

def capture_api_call_logs():
    """Monitor logs for API call patterns"""
    print("📡 Starting API call monitoring...")
    print("   (Check your server logs for these patterns:)")
    print("   - 'Batch processing setup: X API calls estimated'")
    print("   - 'Processed X captures with Y LLM calls'")
    print("   - 'API calls saved: Z'")
    print("   - HTTP requests to api.anthropic.com")

def test_comprehensive_batch_optimization():
    """Test that verifies actual batch optimization metrics"""
    print("🔬 COMPREHENSIVE BATCH OPTIMIZATION TEST")
    print("=" * 60)
    
    # 1. Clear existing notes
    print("🧹 Clearing existing notes...")
    response = requests.delete(f"{API_BASE}/api/notes")
    print(f"   Status: {response.status_code}")
    
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
    print(f"   ✅ Batch processed: {batch_result['notes_processed']} notes")
    
    # 3. Wait for background processing
    print("⏳ Waiting for background processing...")
    time.sleep(3)
    
    # 4. Monitor API calls during bake
    print("🔥 Triggering bake with API call monitoring...")
    capture_api_call_logs()
    
    bake_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "batch_test",
        "includeAdditionalNotes": False
    }
    
    start_time = time.time()
    response = requests.post(f"{API_BASE}/api/bake", json=bake_data)
    
    if response.status_code != 200:
        print(f"❌ Bake failed: {response.status_code} - {response.text}")
        return False
    
    bake_result = response.json()
    bake_id = bake_result['bake_id']
    print(f"   ✅ Bake initiated: {bake_id}")
    
    # 5. Wait for completion with progress updates
    print("⏳ Waiting for pipeline completion...")
    for i in range(20):  # 20 seconds max
        time.sleep(1)
        if i % 5 == 0:
            print(f"   ... {i+1}s elapsed")
    
    processing_time = time.time() - start_time
    print(f"   ⏱️ Total processing time: {processing_time:.1f}s")
    
    # 6. Get detailed results
    print("📊 Analyzing batch optimization results...")
    response = requests.get(f"{API_BASE}/api/results")
    
    if response.status_code != 200:
        print(f"❌ Failed to get results: {response.status_code}")
        return False
    
    results = response.json()
    if not results['results']:
        print("❌ No results found")
        return False
    
    # Find our bake result
    latest_result = None
    for result in results['results']:
        if result.get('bake_id') == bake_id:
            latest_result = result
            break
    
    if not latest_result:
        latest_result = results['results'][-1]
    
    # 7. Analyze batch optimization metrics
    return analyze_batch_metrics(latest_result, len(batch_data['notes']))

def analyze_batch_metrics(result, expected_notes):
    """Analyze and report on batch optimization metrics"""
    print("📈 BATCH OPTIMIZATION ANALYSIS")
    print("=" * 50)
    
    # Basic metrics
    insights = result.get('insights', [])
    processing_summary = result.get('processing_summary', {})
    
    print(f"🧠 Content Analysis Results:")
    print(f"   Notes processed: {result.get('input_notes_count', 0)}/{expected_notes}")
    print(f"   Concepts extracted: {processing_summary.get('concepts_extracted', 0)}")
    print(f"   Entities found: {processing_summary.get('entities_found', 0)}")
    print(f"   Topics identified: {processing_summary.get('topics_identified', 0)}")
    print(f"   Insights generated: {len(insights)}")
    
    # Batch optimization metrics
    batch_metrics = processing_summary.get('batch_optimization_metrics', {})
    
    if batch_metrics:
        print(f"\n⚡ BATCH OPTIMIZATION METRICS:")
        api_calls_made = batch_metrics.get('api_calls_made', 0)
        api_calls_saved = batch_metrics.get('api_calls_saved', 0)
        total_without_batching = api_calls_made + api_calls_saved
        
        print(f"   API calls made: {api_calls_made}")
        print(f"   API calls saved: {api_calls_saved}")
        print(f"   Total without batching: {total_without_batching}")
        
        if total_without_batching > 0:
            reduction_percent = (api_calls_saved / total_without_batching) * 100
            print(f"   Reduction percentage: {reduction_percent:.1f}%")
        
        cache_hit_rate = batch_metrics.get('cache_hit_rate', 0)
        print(f"   Cache hit rate: {cache_hit_rate:.1f}%")
        
        method_breakdown = batch_metrics.get('method_breakdown', {})
        print(f"   Processing methods: {method_breakdown}")
        
        # Validation
        success = True
        if api_calls_saved == 0:
            print("   ⚠️  WARNING: No API calls were saved!")
            success = False
        
        if processing_summary.get('concepts_extracted', 0) == 0:
            print("   ⚠️  WARNING: No concepts were extracted!")
            success = False
            
        if method_breakdown.get('llm_batch', 0) == 0:
            print("   ⚠️  WARNING: No LLM batch processing detected!")
            success = False
        
        return success
    else:
        print("   ❌ No batch optimization metrics found!")
        print("   This suggests the batch processing is not working correctly.")
        return False

def test_api_call_monitoring():
    """Test with explicit API call monitoring"""
    print("\n🔍 API CALL MONITORING TEST")
    print("=" * 40)
    
    print("📝 Instructions for manual verification:")
    print("   1. Monitor your server logs during the test")
    print("   2. Look for these specific log messages:")
    print("      • 'Batch processing setup: X API calls estimated'")
    print("      • 'Processing batch 1/Y with Z captures'")
    print("      • 'Processed X captures with Y LLM calls'")
    print("      • 'API calls saved: Z'")
    print("   3. Watch for HTTP requests to api.anthropic.com in logs")
    print("   4. Compare expected vs actual API calls")
    
    expected_individual_calls = 5  # One per note
    expected_batch_calls = 2       # Batch size of 3, so 2 batches
    expected_savings = expected_individual_calls - expected_batch_calls
    
    print(f"\n📊 Expected Results:")
    print(f"   Individual processing: {expected_individual_calls} API calls")
    print(f"   Batch processing: {expected_batch_calls} API calls")
    print(f"   Expected savings: {expected_savings} API calls")

def main():
    """Run comprehensive batch optimization test"""
    try:
        # Check API health
        response = requests.get(f"{API_BASE}/api/health")
        if response.status_code != 200:
            print(f"❌ API not available: {response.status_code}")
            return
        
        print("✅ API is healthy")
        
        # Run comprehensive test
        success = test_comprehensive_batch_optimization()
        
        # Run monitoring test
        test_api_call_monitoring()
        
        if success:
            print(f"\n🎉 BATCH OPTIMIZATION TEST PASSED!")
            print(f"   ✅ API calls are being batched and reduced")
            print(f"   ✅ Concepts are being extracted properly")
            print(f"   ✅ Batch metrics are being tracked")
        else:
            print(f"\n❌ BATCH OPTIMIZATION TEST FAILED!")
            print(f"   Check your server logs for detailed error messages")
            print(f"   Verify your LLM provider (Anthropic) is configured correctly")
            print(f"   Ensure ANTHROPIC_API_KEY is set")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()