#!/usr/bin/env python3
"""
Test script to verify YAML prompt configuration loading works correctly.
"""

import sys
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from extractor_llm import PromptTemplates

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_yaml_loading():
    """Test that YAML configuration loads correctly."""
    logger.info("Testing YAML prompt configuration loading...")
    
    try:
        # Initialize PromptTemplates (should load from prompts.yaml)
        templates = PromptTemplates()
        
        # Test system prompt
        system_prompt = templates.get_system_prompt()
        logger.info(f"✓ System prompt loaded: {len(system_prompt)} characters")
        
        # Test confidence scores
        question_conf = templates.get_confidence_score('question')
        strategy_conf = templates.get_confidence_score('strategy') 
        analysis_conf = templates.get_confidence_score('analysis')
        logger.info(f"✓ Confidence scores - Question: {question_conf}, Strategy: {strategy_conf}, Analysis: {analysis_conf}")
        
        # Test predicates
        question_preds = templates.get_predicates('question')
        strategy_preds = templates.get_predicates('strategy')
        logger.info(f"✓ Predicates - Question: {question_preds}, Strategy: {strategy_preds}")
        
        # Test template generation with sample data
        sample_messages = [
            {'author': 'user1', 'clean_text': 'What is the best DCA strategy?'},
            {'author': 'user2', 'clean_text': 'I recommend weekly DCA with TQQQ'}
        ]
        
        question_prompt = templates.get_question_prompt(sample_messages)
        logger.info(f"✓ Question prompt generated: {len(question_prompt)} characters")
        
        strategy_prompt = templates.get_strategy_prompt(sample_messages)
        logger.info(f"✓ Strategy prompt generated: {len(strategy_prompt)} characters")
        
        # Test Q&A linking
        questions = [{'message_id': 'q1', 'author': 'user1', 'clean_text': 'What is DCA?'}]
        answers = [{'message_id': 'a1', 'author': 'user2', 'clean_text': 'DCA is dollar cost averaging'}]
        
        qa_prompt = templates.get_qa_linking_prompt(questions, answers)
        logger.info(f"✓ Q&A linking prompt generated: {len(qa_prompt)} characters")
        
        logger.info("✅ All YAML configuration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ YAML configuration test failed: {e}")
        return False


def test_custom_config_path():
    """Test loading from a custom config path."""
    logger.info("Testing custom config path...")
    
    config_path = Path(__file__).parent / "prompts.yaml"
    
    try:
        templates = PromptTemplates(str(config_path))
        system_prompt = templates.get_system_prompt()
        logger.info(f"✓ Custom config loaded successfully: {len(system_prompt)} characters")
        return True
    except Exception as e:
        logger.error(f"❌ Custom config test failed: {e}")
        return False


def test_missing_config():
    """Test behavior when config file is missing."""
    logger.info("Testing missing config file handling...")
    
    try:
        templates = PromptTemplates("nonexistent_config.yaml")
        logger.error("❌ Should have failed for missing config file")
        return False
    except FileNotFoundError:
        logger.info("✓ Correctly handled missing config file")
        return True
    except Exception as e:
        logger.error(f"❌ Unexpected error for missing config: {e}")
        return False


if __name__ == "__main__":
    logger.info("🧪 Testing YAML Prompt Configuration")
    
    # Run tests
    test1 = test_yaml_loading()
    test2 = test_custom_config_path() 
    test3 = test_missing_config()
    
    # Summary
    passed = sum([test1, test2, test3])
    total = 3
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! YAML configuration is working correctly.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Check the configuration.")
        sys.exit(1)