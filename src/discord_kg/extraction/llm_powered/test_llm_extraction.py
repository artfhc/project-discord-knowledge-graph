#!/usr/bin/env python3
"""
Test script for LLM-powered Step 3 extraction.

This script demonstrates how to use the LLM extractor with cost estimation.
"""

import json
import logging
import os
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def estimate_cost(input_file: str, provider: str = "openai", batch_size: int = 20):
    """Estimate cost for LLM extraction without actually running it."""
    
    # Load messages to count
    messages = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))
    
    # Group by segment
    segments = {}
    for msg in messages:
        segment_id = msg['segment_id']
        if segment_id not in segments:
            segments[segment_id] = []
        segments[segment_id].append(msg)
    
    # Estimate tokens and cost
    total_chars = sum(len(msg['clean_text']) for msg in messages)
    estimated_tokens = total_chars // 4  # Rough approximation: 4 chars per token
    
    # Estimate requests (segment batching)
    estimated_requests = 0
    for segment_messages in segments.values():
        # Group by message type
        by_type = {}
        for msg in segment_messages:
            msg_type = msg['type']
            if msg_type not in by_type:
                by_type[msg_type] = []
            by_type[msg_type].append(msg)
        
        # Count batches per type
        for msg_type, type_messages in by_type.items():
            num_batches = (len(type_messages) + batch_size - 1) // batch_size
            estimated_requests += num_batches
    
    # Cost per 1K tokens
    if provider == "openai":
        cost_per_1k = 0.0015 + 0.002  # Input + output for GPT-3.5
        provider_name = "OpenAI GPT-3.5-turbo"
    else:  # claude
        cost_per_1k = 0.00025 + 0.00125  # Input + output for Claude Haiku
        provider_name = "Claude 3 Haiku"
    
    estimated_cost = (estimated_tokens * cost_per_1k / 1000) * 1.5  # 1.5x for safety margin
    
    logger.info(f"\n=== Cost Estimation for {provider_name} ===")
    logger.info(f"Messages: {len(messages)}")
    logger.info(f"Segments: {len(segments)}")
    logger.info(f"Estimated tokens: {estimated_tokens:,}")
    logger.info(f"Estimated requests: {estimated_requests}")
    logger.info(f"Estimated cost: ${estimated_cost:.2f}")
    logger.info(f"Batch size: {batch_size}")
    
    return estimated_cost


def test_llm_extractor_dry_run():
    """Test the LLM extractor with cost estimation (no actual API calls)."""
    
    # Find input file
    input_candidates = [
        "../preprocessing/sample_results.jsonl",
        "../preprocessing/sample_results_5000.jsonl"
    ]
    
    input_file = None
    for candidate in input_candidates:
        if Path(candidate).exists():
            input_file = candidate
            break
    
    if not input_file:
        logger.error("No preprocessing output found. Run Step 2 first.")
        return False
    
    logger.info(f"Analyzing file: {input_file}")
    
    # Estimate costs for different configurations
    logger.info("\n=== Cost Analysis ===")
    
    # OpenAI costs
    estimate_cost(input_file, "openai", batch_size=10)  # High accuracy
    estimate_cost(input_file, "openai", batch_size=20)  # Balanced  
    estimate_cost(input_file, "openai", batch_size=50)  # Efficient
    
    # Claude costs
    estimate_cost(input_file, "claude", batch_size=10)  # High accuracy
    estimate_cost(input_file, "claude", batch_size=20)  # Balanced
    estimate_cost(input_file, "claude", batch_size=50)  # Efficient
    
    return True


def test_with_api_keys():
    """Test with actual API if keys are available."""
    
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_claude = bool(os.getenv('ANTHROPIC_API_KEY'))
    openai_model = os.getenv('OPENAI_MODEL')
    claude_model = os.getenv('ANTHROPIC_MODEL')
    
    logger.info(f"\n=== API Key Status ===")
    logger.info(f"OpenAI API Key: {'✓ Available' if has_openai else '✗ Not set'}")
    if openai_model:
        logger.info(f"OpenAI Model: {openai_model} (from OPENAI_MODEL env var)")
    else:
        logger.info(f"OpenAI Model: gpt-3.5-turbo (default)")
        
    logger.info(f"Claude API Key: {'✓ Available' if has_claude else '✗ Not set'}")
    if claude_model:
        logger.info(f"Claude Model: {claude_model} (from ANTHROPIC_MODEL env var)")
    else:
        logger.info(f"Claude Model: claude-3-haiku-20240307 (default)")
    
    if not has_openai and not has_claude:
        logger.info("\nTo test with real APIs, set environment variables:")
        logger.info("export OPENAI_API_KEY='your-key-here'")
        logger.info("export OPENAI_MODEL='gpt-4'  # Optional: override default model")
        logger.info("export ANTHROPIC_API_KEY='your-key-here'")
        logger.info("export ANTHROPIC_MODEL='claude-3-sonnet-20240229'  # Optional: override default model")
        return False
    
    # If we have keys, we could run a small test
    if has_openai or has_claude:
        logger.info("\n=== Ready for LLM Testing ===")
        logger.info("You can now run:")
        
        provider = "openai" if has_openai else "claude"
        logger.info(f"python extractor_llm.py ../preprocessing/sample_results.jsonl llm_output.jsonl --provider {provider} --batch-size 20")
        
        return True


def create_sample_test():
    """Create a minimal test to verify LLM integration without high costs."""
    
    # Create tiny test file
    sample_messages = [
        {
            "message_id": "test_001",
            "segment_id": "test_segment_1",
            "type": "question",
            "author": "user1",
            "timestamp": "2024-01-01T10:00:00+00:00",
            "clean_text": "What's the best DCA strategy for TQQQ?",
            "mentions": [],
            "reply_to": None
        },
        {
            "message_id": "test_002",
            "segment_id": "test_segment_1", 
            "type": "answer",
            "author": "user2",
            "timestamp": "2024-01-01T10:05:00+00:00",
            "clean_text": "I recommend starting small with weekly DCA and using the symphony algorithm",
            "mentions": ["user1"],
            "reply_to": "test_001"
        }
    ]
    
    # Save sample
    sample_file = "llm_test_sample.jsonl"
    with open(sample_file, 'w') as f:
        for msg in sample_messages:
            f.write(json.dumps(msg) + '\n')
    
    logger.info(f"Created minimal test file: {sample_file}")
    
    # Estimate cost (should be < $0.01)
    estimate_cost(sample_file, "openai", batch_size=10)
    
    logger.info("\nTo test LLM extraction on this sample:")
    logger.info(f"python extractor_llm.py {sample_file} llm_sample_output.jsonl --provider openai")
    
    return sample_file


if __name__ == "__main__":
    logger.info("🧪 LLM Extraction Testing")
    
    # Test 1: Cost estimation
    logger.info("\n--- Test 1: Cost Estimation ---")
    estimation_success = test_llm_extractor_dry_run()
    
    # Test 2: API key check
    logger.info("\n--- Test 2: API Configuration ---")
    api_ready = test_with_api_keys()
    
    # Test 3: Create sample
    logger.info("\n--- Test 3: Sample Generation ---")
    sample_file = create_sample_test()
    
    # Summary
    logger.info(f"\n=== Summary ===")
    if estimation_success:
        logger.info("✓ Cost estimation completed")
    if api_ready:
        logger.info("✓ API keys configured")
    if sample_file:
        logger.info(f"✓ Sample test file ready: {sample_file}")
        
    logger.info("\nNext steps:")
    logger.info("1. Set API keys if not already done")
    logger.info("2. Run on sample data first to test")
    logger.info("3. Use appropriate batch size for your budget")
    logger.info("4. Monitor costs during execution")