#!/usr/bin/env python3
"""
Direct test of LLM batching functionality
"""
import sys
import os
import logging
from datetime import datetime, timezone

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Add your project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nodes.content_analysis import ContentAnalysisNode

# Set up detailed logging to see API calls
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_crypto_test_captures():
    """Create test captures that should trigger LLM processing"""
    return [
        {
            'id': 'crypto_1',
            'content': 'Automated Market Makers (AMMs) are decentralized exchange protocols that use mathematical formulas to price assets. Instead of order books, AMMs rely on liquidity pools where users provide token pairs. The constant product formula x*y=k ensures continuous liquidity and automatic price discovery based on supply and demand.',
            'url': 'https://uniswap.org/docs',
            'metadata': {
                'domain': 'uniswap.org',
                'word_count': 52,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'content_category': 'documentation',
                'has_code': False,
                'capture_trigger': 'test'
            }
        },
        {
            'id': 'crypto_2', 
            'content': 'Yield farming involves providing liquidity to DeFi protocols in exchange for token rewards. Farmers analyze APY rates, impermanent loss risks, and token emission schedules. Popular strategies include single-asset staking, liquidity provision to AMMs, and participating in liquidity mining programs across multiple protocols.',
            'url': 'https://compound.finance/governance',
            'metadata': {
                'domain': 'compound.finance',
                'word_count': 48,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'content_category': 'educational',
                'has_code': False,
                'capture_trigger': 'test'
            }
        },
        {
            'id': 'crypto_3',
            'content': 'Layer 2 scaling solutions address Ethereum\'s scalability limitations through off-chain transaction processing. Optimistic rollups like Arbitrum assume transactions are valid and use fraud proofs for disputes. ZK-rollups use zero-knowledge proofs to verify transaction validity without revealing transaction details.',
            'url': 'https://ethereum.org/layer2',
            'metadata': {
                'domain': 'ethereum.org',
                'word_count': 45,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'content_category': 'technical',
                'has_code': False,
                'capture_trigger': 'test'
            }
        },
        {
            'id': 'crypto_4',
            'content': 'Cross-chain bridges enable asset transfers between different blockchain networks. Bridge protocols lock tokens on the source chain and mint equivalent tokens on the destination chain. Security models vary from trusted validators to cryptographic proofs, with trade-offs between security and functionality.',
            'url': 'https://bridge.connext.network/docs',
            'metadata': {
                'domain': 'connext.network',
                'word_count': 42,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'content_category': 'technical',
                'has_code': False,
                'capture_trigger': 'test'
            }
        }
    ]

class APICallCounter:
    """Monitor and count API calls to LLM"""
    def __init__(self):
        self.api_call_count = 0
        self.original_chat_completion = None
    
    def monitor_api_calls(self, content_node):
        """Wrap the LLM client to count API calls"""
        if content_node.llm_client:
            self.original_chat_completion = content_node.llm_client.chat_completion
            content_node.llm_client.chat_completion = self._counted_chat_completion
    
    def _counted_chat_completion(self, messages, **kwargs):
        """Wrapper that counts API calls"""
        self.api_call_count += 1
        print(f"🔥 API CALL #{self.api_call_count}")
        print(f"   Messages: {len(messages)}")
        print(f"   Model: {kwargs.get('model', 'default')}")
        print(f"   Max tokens: {kwargs.get('max_tokens', 'default')}")
        
        # Call the original method
        return self.original_chat_completion(messages, **kwargs)

def test_direct_llm_batching():
    """Test LLM batching directly"""
    print("🧪 DIRECT LLM BATCHING TEST")
    print("=" * 50)
    
    # Create content analysis node
    print("🔧 Initializing ContentAnalysisNode...")
    content_node = ContentAnalysisNode()
    
    # Set up API call monitoring
    api_counter = APICallCounter()
    api_counter.monitor_api_calls(content_node)
    
    # Check LLM availability
    if not content_node.llm_client or not content_node.llm_client.is_available():
        print("❌ LLM client not available!")
        print("   Check your ANTHROPIC_API_KEY environment variable")
        return False
    
    print(f"✅ LLM client available: {content_node.llm_client.get_provider_name()}")
    
    # Create test captures
    test_captures = create_crypto_test_captures()
    print(f"📝 Created {len(test_captures)} test captures")
    
    # Show what processing method each capture should use
    print("📊 Analyzing capture processing methods...")
    for i, capture in enumerate(test_captures, 1):
        content_preview = capture['content'][:50] + "..."
        word_count = capture['metadata']['word_count']
        
        # Check if it will use rule-based
        uses_rule_based = content_node._can_use_rule_based_analysis(capture)
        method = "RULE-BASED" if uses_rule_based else "LLM"
        
        print(f"   {i}. {method} ({word_count} words): {content_preview}")
    
    # Test categorization
    print("\n🔍 Testing capture categorization...")
    categories = content_node._categorize_captures_for_processing(test_captures)
    
    print(f"   Cached: {len(categories['cached'])}")
    print(f"   Rule-based: {len(categories['rule_based'])}")
    print(f"   LLM required: {len(categories['llm_required'])}")
    
    if len(categories['llm_required']) == 0:
        print("⚠️  WARNING: No captures require LLM processing!")
        print("   This means batching won't be tested properly.")
        return False
    
    # Create shared state and run analysis
    print(f"\n⚡ Running content analysis with API call monitoring...")
    shared_state = {
        'session_id': 'direct_test',
        'raw_captures': test_captures,
        'pipeline_metadata': {}
    }
    
    # Run the full content analysis pipeline
    print("📋 Running prep phase...")
    prep_result = content_node.prep(shared_state)
    
    if 'error' in prep_result:
        print(f"❌ Prep failed: {prep_result['error']}")
        return False
    
    print("⚡ Running exec phase...")
    api_counter.api_call_count = 0  # Reset counter
    exec_result = content_node.exec(prep_result)
    
    if 'error' in exec_result:
        print(f"❌ Exec failed: {exec_result['error']}")
        return False
    
    print("📤 Running post phase...")
    post_result = content_node.post(shared_state, prep_result, exec_result)
    
    # Analyze results
    print(f"\n📊 RESULTS ANALYSIS")
    print("=" * 30)
    
    actual_api_calls = api_counter.api_call_count
    expected_individual_calls = len(categories['llm_required'])
    expected_batch_calls = (len(categories['llm_required']) + content_node.batch_size - 1) // content_node.batch_size
    
    print(f"🔥 API Call Analysis:")
    print(f"   Actual API calls made: {actual_api_calls}")
    print(f"   Expected without batching: {expected_individual_calls}")
    print(f"   Expected with batching: {expected_batch_calls}")
    
    # Check batch metrics
    batch_metrics = exec_result.get('batch_metrics', {})
    if batch_metrics:
        print(f"\n📈 Batch Metrics from Results:")
        print(f"   API calls made: {batch_metrics.get('api_calls_made', 0)}")
        print(f"   API calls saved: {batch_metrics.get('api_calls_saved', 0)}")
        print(f"   Method breakdown: {batch_metrics.get('method_breakdown', {})}")
    
    # Check content extraction
    extracted_concepts = exec_result.get('extracted_concepts', {})
    print(f"\n🧠 Content Extraction:")
    print(f"   Learning concepts: {len(extracted_concepts.get('learning_concepts', []))}")
    print(f"   Key terms: {len(extracted_concepts.get('key_terms', {}))}")
    print(f"   Entities: {len(extracted_concepts.get('entities', {}))}")
    
    # Validation
    success = True
    
    if actual_api_calls <= 0:
        print("❌ No API calls were made!")
        success = False
    elif actual_api_calls >= expected_individual_calls:
        print("⚠️  API calls NOT reduced by batching!")
        success = False
    else:
        saved_calls = expected_individual_calls - actual_api_calls
        print(f"✅ Batching saved {saved_calls} API calls!")
    
    if len(extracted_concepts.get('learning_concepts', [])) == 0:
        print("❌ No learning concepts extracted!")
        success = False
    
    return success

def main():
    """Run the direct LLM batching test"""
    try:
        # Check environment variables first
        print("🔧 Environment Check:")
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            print(f"   ✅ ANTHROPIC_API_KEY: ...{anthropic_key[-4:]}")
        else:
            print("   ❌ ANTHROPIC_API_KEY: Not found")
            print("   💡 Make sure your .env file has: ANTHROPIC_API_KEY=your_key_here")
            return
        
        success = test_direct_llm_batching()
        
        if success:
            print(f"\n🎉 BATCHING TEST PASSED!")
            print(f"   ✅ LLM API calls are being batched")
            print(f"   ✅ Content is being analyzed properly")
            print(f"   ✅ Batch optimization is working")
        else:
            print(f"\n❌ BATCHING TEST FAILED!")
            print(f"   Check the output above for specific issues")
            
        print(f"\n💡 Next Steps:")
        print(f"   - Run your API test again to see if batching works end-to-end")
        print(f"   - Check server logs for 'HTTP Request: POST https://api.anthropic.com'")
        print(f"   - Verify ANTHROPIC_API_KEY is configured correctly")
        
    except Exception as e:
        print(f"❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()