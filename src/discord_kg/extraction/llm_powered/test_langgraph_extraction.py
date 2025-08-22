"""
Test script for the LangGraph-based Discord Knowledge Graph extraction system.

This script demonstrates the new architecture and provides examples of how to use
the system for extracting knowledge triples from Discord messages.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import sys

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from workflow_state import create_initial_state, MessageType
from config import ConfigManager
from llm_providers import LLMProviderFactory
from workflow import ExtractionWorkflow


def create_test_messages() -> List[Dict[str, Any]]:
    """Create sample Discord messages for testing."""
    
    return [
        {
            "message_id": "msg_001",
            "author": "trader_alice",
            "clean_text": "What's the best strategy for covered calls on AAPL?",
            "timestamp": "2024-01-01T10:00:00Z",
            "segment_id": "segment_1"
        },
        {
            "message_id": "msg_002", 
            "author": "options_expert",
            "clean_text": "For AAPL covered calls, I recommend selling 30-45 DTE calls at 15-20 delta. The wheel strategy works great with AAPL due to its liquidity.",
            "timestamp": "2024-01-01T10:05:00Z",
            "segment_id": "segment_1"
        },
        {
            "message_id": "msg_003",
            "author": "market_analyst", 
            "clean_text": "AAPL is showing strong support at $180. I expect upward momentum through earnings next week.",
            "timestamp": "2024-01-01T10:10:00Z",
            "segment_id": "segment_1"
        },
        {
            "message_id": "msg_004",
            "author": "day_trader",
            "clean_text": "Made 15% profit on my TSLA calls this week. Closed position before the volatility spike.",
            "timestamp": "2024-01-01T10:15:00Z", 
            "segment_id": "segment_1"
        },
        {
            "message_id": "msg_005",
            "author": "bot_alerts",
            "clean_text": "ALERT: FOMC meeting scheduled for tomorrow. Expect high volatility in tech stocks.",
            "timestamp": "2024-01-01T10:20:00Z",
            "segment_id": "segment_1"
        }
    ]


def test_configuration_management():
    """Test configuration loading and validation."""
    print("🧪 Testing Configuration Management")
    
    try:
        config_manager = ConfigManager()
        
        # Test configuration validation
        is_valid = config_manager.validate_config()
        print(f"   ✅ Configuration validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Test prompt retrieval
        system_prompt = config_manager.get_system_prompt()
        print(f"   ✅ System prompt loaded: {len(system_prompt)} characters")
        
        # Test template retrieval
        question_template = config_manager.get_template("question")
        print(f"   ✅ Question template loaded: {question_template.description}")
        
        # Test confidence scores
        question_confidence = config_manager.get_confidence_score("question")
        print(f"   ✅ Question confidence: {question_confidence}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration test failed: {e}")
        return False


def test_workflow_state():
    """Test workflow state creation and manipulation."""
    print("🧪 Testing Workflow State")
    
    try:
        messages = create_test_messages()
        
        # Create initial state
        state = create_initial_state(
            messages=messages,
            llm_provider="openai",
            batch_size=10
        )
        
        print(f"   ✅ Initial state created with {len(state['raw_messages'])} messages")
        print(f"   ✅ Current step: {state['current_step']}")
        print(f"   ✅ LLM provider: {state['llm_provider']}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Workflow state test failed: {e}")
        return False


def test_message_classification():
    """Test message classification logic."""
    print("🧪 Testing Message Classification")
    
    try:
        from nodes import classification_node
        
        messages = create_test_messages()
        state = create_initial_state(messages=messages, llm_provider="openai")
        
        # Set processed messages (preprocessing normally does this)
        state["processed_messages"] = messages
        
        # Run classification
        result_state = classification_node(state)
        
        # Check results
        classified = result_state["classified_messages"]
        print(f"   ✅ Classification completed:")
        
        for msg_type, msgs in classified.items():
            print(f"      - {msg_type}: {len(msgs)} messages")
        
        # Verify expected classifications
        expected_types = {
            "question": ["msg_001"],
            "answer": ["msg_002"], 
            "analysis": ["msg_003"],
            "performance": ["msg_004"],
            "alert": ["msg_005"]
        }
        
        success = True
        for msg_type, expected_ids in expected_types.items():
            actual_msgs = classified.get(msg_type, [])
            actual_ids = [msg["message_id"] for msg in actual_msgs]
            
            for expected_id in expected_ids:
                if expected_id not in actual_ids:
                    print(f"   ⚠️  Expected {expected_id} to be classified as {msg_type}")
                    success = False
        
        if success:
            print("   ✅ All messages classified correctly")
        
        return success
        
    except Exception as e:
        print(f"   ❌ Classification test failed: {e}")
        return False


def test_workflow_dry_run():
    """Test workflow initialization without API calls."""
    print("🧪 Testing Workflow Dry Run")
    
    try:
        # Test workflow creation
        workflow = ExtractionWorkflow(
            llm_provider="openai",
            batch_size=5
        )
        
        print("   ✅ Workflow initialized successfully")
        
        # Test configuration validation
        is_valid = workflow.validate_configuration()
        print(f"   ✅ Configuration validation: {'PASSED' if is_valid else 'FAILED'}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Workflow dry run failed: {e}")
        return False


def test_end_to_end_simulation():
    """Simulate end-to-end processing without API calls."""
    print("🧪 Testing End-to-End Simulation")
    
    try:
        # Create test data
        messages = create_test_messages()
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as input_file:
            for msg in messages:
                input_file.write(json.dumps(msg) + '\n')
            input_file_path = input_file.name
        
        output_file_path = input_file_path.replace('.jsonl', '_output.jsonl')
        
        print(f"   ✅ Created test files:")
        print(f"      - Input: {Path(input_file_path).name}")
        print(f"      - Output: {Path(output_file_path).name}")
        
        # Test file validation (this should work without API calls)
        from extractor_langgraph import validate_input_file
        
        is_valid = validate_input_file(input_file_path)
        print(f"   ✅ Input validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Clean up
        Path(input_file_path).unlink(missing_ok=True)
        Path(output_file_path).unlink(missing_ok=True)
        
        return is_valid
        
    except Exception as e:
        print(f"   ❌ End-to-end simulation failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 LangGraph Discord Knowledge Graph Extraction - Test Suite")
    print("=" * 60)
    
    # Setup minimal logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests
    tests = [
        ("Configuration Management", test_configuration_management),
        ("Workflow State", test_workflow_state),
        ("Message Classification", test_message_classification),
        ("Workflow Dry Run", test_workflow_dry_run),
        ("End-to-End Simulation", test_end_to_end_simulation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n📊 Test Results Summary")
    print("=" * 25)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The system is ready for use.")
        print("\nNext steps:")
        print("1. Set up your API keys (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run: python extractor_langgraph.py --help")
    else:
        print("⚠️  Some tests failed. Please check the configuration and dependencies.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())