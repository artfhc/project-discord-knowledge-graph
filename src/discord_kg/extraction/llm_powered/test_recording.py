#!/usr/bin/env python3
"""
Simple test script to demonstrate LLM call recording functionality.
"""

from enable_recording import enable_recording_in_extractor_langgraph, show_recording_stats
from llm_recorder import get_call_stats

# Sample test messages (similar to your real data structure)
test_messages = [
    {
        "message_id": "test_001",
        "segment_id": "test_segment_1", 
        "type": "question",
        "author": "test_user1",
        "timestamp": "2024-01-01T10:00:00+00:00",
        "clean_text": "What's the best DCA strategy for TQQQ?"
    },
    {
        "message_id": "test_002",
        "segment_id": "test_segment_1",
        "type": "answer", 
        "author": "test_user2",
        "timestamp": "2024-01-01T10:05:00+00:00",
        "clean_text": "I recommend weekly DCA with small amounts"
    }
]

def test_basic_recording():
    """Test basic recording functionality."""
    print("🧪 Testing LLM Call Recording System")
    print("=" * 50)
    
    # Enable recording for this test
    print("\n1. Enabling recording...")
    success = enable_recording_in_extractor_langgraph("test_experiment")
    
    if not success:
        print("❌ Failed to enable recording")
        return False
    
    # Test the recorded LLM client
    print("\n2. Testing recorded LLM client...")
    try:
        from recorded_llm_providers import RecordedLLMClient
        
        # Create client (this will fail without API keys, but that's OK for testing)
        client = RecordedLLMClient("openai")
        print(f"✅ Created RecordedLLMClient with model: {client.model}")
        
        # Simulate a call (will fail due to no API key, but recording should work)
        try:
            response = client.extract_triples(
                messages=test_messages,
                system_prompt="You are a test system",
                user_prompt="Extract triples from: test message",
                template_type="test",
                workflow_step="testing"
            )
            print("✅ LLM call completed (unexpected success!)")
        except Exception as e:
            print(f"⚠️  LLM call failed (expected): {str(e)[:100]}...")
            print("   (This is expected without valid API keys)")
        
    except Exception as e:
        print(f"❌ Error testing recorded client: {e}")
        return False
    
    # Check if anything was recorded
    print("\n3. Checking recording results...")
    stats = get_call_stats()
    print(f"   • Total calls recorded: {stats.get('total_calls', 0)}")
    print(f"   • Successful calls: {stats.get('successful_calls', 0)}")
    
    if stats.get('total_calls', 0) > 0:
        print("✅ Recording system is working!")
        show_recording_stats()
    else:
        print("⚠️  No calls were recorded")
    
    print("\n4. Testing database access...")
    try:
        from llm_recorder import get_storage
        storage = get_storage()
        recent_calls = storage.get_calls(limit=5)
        print(f"✅ Retrieved {len(recent_calls)} recent call records")
        
        if recent_calls:
            latest = recent_calls[0]
            print(f"   • Latest call: {latest['timestamp']} - {latest['template_type']}")
    except Exception as e:
        print(f"❌ Database access error: {e}")
        return False
    
    print("\n🎉 Recording system test completed!")
    print("\n💡 Next steps:")
    print("   • Set your API keys (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
    print("   • Run: enable_recording_in_extractor_langgraph('my_experiment')")
    print("   • Then run your normal extraction workflow")
    print("   • Check results with: show_recording_stats()")
    
    return True

if __name__ == "__main__":
    test_basic_recording()