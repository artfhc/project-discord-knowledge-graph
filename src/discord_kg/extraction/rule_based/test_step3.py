#!/usr/bin/env python3
"""
Test script for Step 3 extraction according to README specification.
"""

import json
import logging
from pathlib import Path
from extractor import Step3Extractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_step3_extraction():
    """Test the Step 3 extractor on real preprocessing data."""
    
    # Find input file
    input_candidates = [
        "../../preprocessing/sample_results.jsonl",
        "../../preprocessing/sample_results_5000.jsonl"
    ]
    
    input_file = None
    for candidate in input_candidates:
        if Path(candidate).exists():
            input_file = candidate
            break
    
    if not input_file:
        logger.error("No preprocessing output found. Run Step 2 first.")
        return False
    
    output_file = "step3_test_results.jsonl"
    
    logger.info(f"Testing Step 3 extraction: {input_file} -> {output_file}")
    
    # Run extraction
    extractor = Step3Extractor()
    num_triples = extractor.process_file(input_file, output_file)
    
    # Analyze results
    analyze_results(output_file)
    
    logger.info(f"✓ Step 3 test completed: {num_triples} triples extracted")
    return True


def analyze_results(results_file: str):
    """Analyze the extraction results by type and quality."""
    
    if not Path(results_file).exists():
        logger.error(f"Results file not found: {results_file}")
        return
    
    triples = []
    with open(results_file, 'r') as f:
        for line in f:
            if line.strip():
                triples.append(json.loads(line))
    
    logger.info(f"\n=== Step 3 Extraction Analysis ===")
    logger.info(f"Total triples: {len(triples)}")
    
    # Group by predicate
    predicates = {}
    for triple in triples:
        pred = triple['predicate']
        if pred not in predicates:
            predicates[pred] = []
        predicates[pred].append(triple)
    
    logger.info(f"\nTriples by predicate (message type strategy):")
    for pred, triple_list in sorted(predicates.items()):
        logger.info(f"  {pred}: {len(triple_list)} triples")
    
    # Show confidence distribution
    confidences = [t['confidence'] for t in triples]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    logger.info(f"\nAverage confidence: {avg_confidence:.3f}")
    
    # Show high-confidence samples
    logger.info(f"\nHigh-confidence triple samples:")
    high_confidence = sorted(triples, key=lambda x: x['confidence'], reverse=True)[:5]
    for i, triple in enumerate(high_confidence, 1):
        logger.info(f"  {i}. [{triple['subject']}] --{triple['predicate']}--> [{triple['object']}] (conf: {triple['confidence']:.2f})")
    
    # Check Q&A linking
    qa_links = [t for t in triples if t['predicate'] == 'answered_by']
    logger.info(f"\nQ&A links found: {len(qa_links)}")
    
    # Segment distribution
    segments = set(t['segment_id'] for t in triples)
    logger.info(f"Triples distributed across {len(segments)} segments")


def create_sample_test():
    """Create a small sample test to verify extraction logic."""
    
    sample_messages = [
        {
            "message_id": "test_001",
            "segment_id": "test_segment_1",
            "type": "question",
            "author": "user1",
            "timestamp": "2024-01-01T10:00:00+00:00",
            "clean_text": "What's the best strategy for DCA with TQQQ?",
            "mentions": [],
            "reply_to": None
        },
        {
            "message_id": "test_002", 
            "segment_id": "test_segment_1",
            "type": "answer",
            "author": "user2",
            "timestamp": "2024-01-01T10:05:00+00:00",
            "clean_text": "I recommend starting with small amounts and using the symphony algorithm for timing.",
            "mentions": ["user1"],
            "reply_to": "test_001"
        },
        {
            "message_id": "test_003",
            "segment_id": "test_segment_2", 
            "type": "alert",
            "author": "bot",
            "timestamp": "2024-01-01T11:00:00+00:00",
            "clean_text": "Alert: FOMC meeting starts in 1 hour, expect high volatility",
            "mentions": [],
            "reply_to": None
        },
        {
            "message_id": "test_004",
            "segment_id": "test_segment_3",
            "type": "strategy", 
            "author": "trader",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "clean_text": "The wheel strategy with covered calls on AAPL has been working great",
            "mentions": [],
            "reply_to": None
        },
        {
            "message_id": "test_005",
            "segment_id": "test_segment_4",
            "type": "performance",
            "author": "investor", 
            "timestamp": "2024-01-01T13:00:00+00:00",
            "clean_text": "Made +15% profit this month using iron condor on SPY",
            "mentions": [],
            "reply_to": None
        }
    ]
    
    # Save sample
    sample_file = "sample_test_input.jsonl"
    with open(sample_file, 'w') as f:
        for msg in sample_messages:
            f.write(json.dumps(msg) + '\n')
    
    logger.info(f"Created sample test file: {sample_file}")
    
    # Test extraction
    extractor = Step3Extractor()
    triples = extractor.extract_triples(sample_messages)
    
    logger.info(f"\n=== Sample Test Results ===")
    logger.info(f"Extracted {len(triples)} triples from {len(sample_messages)} sample messages")
    
    for i, triple in enumerate(triples, 1):
        logger.info(f"  {i}. [{triple.subject}] --{triple.predicate}--> [{triple.object}] (conf: {triple.confidence:.2f})")
    
    return len(triples) > 0


if __name__ == "__main__":
    logger.info("Starting Step 3 extraction tests...")
    
    # Test 1: Sample data
    logger.info("\n--- Test 1: Sample Data ---")
    sample_success = create_sample_test()
    
    # Test 2: Real preprocessing data
    logger.info("\n--- Test 2: Real Data ---")
    real_success = test_step3_extraction()
    
    if sample_success and real_success:
        logger.info("\n✓ All Step 3 tests passed!")
    else:
        logger.error("\n✗ Some tests failed")