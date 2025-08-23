"""
Configuration and utilities for LLM call recording.

This module provides easy configuration and setup for recording LLM calls
with minimal changes to existing code.
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class RecordingConfig:
    """Configuration for LLM call recording."""
    
    def __init__(self):
        # Check environment variables for configuration
        self.enabled = os.getenv("ENABLE_LLM_RECORDING", "false").lower() == "true"
        self.experiment_name = os.getenv("LLM_EXPERIMENT_NAME")
        self.storage_path = os.getenv("LLM_RECORDING_PATH", "bin/llm_evaluation/llm_calls.db")
        self.recording_level = os.getenv("LLM_RECORDING_LEVEL", "full")  # full, basic, minimal
        
    def setup_recording(self, experiment_name: Optional[str] = None) -> bool:
        """Setup and enable recording with the given experiment name."""
        try:
            from llm_recorder import enable_recording
            
            # Use provided experiment name or fallback to config/env
            exp_name = experiment_name or self.experiment_name or "default_experiment"
            
            enable_recording(exp_name)
            logger.info(f"LLM recording enabled for experiment: {exp_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup LLM recording: {e}")
            return False
    
    def disable_recording(self):
        """Disable LLM call recording."""
        try:
            from llm_recorder import disable_recording
            disable_recording()
            logger.info("LLM recording disabled")
        except Exception as e:
            logger.error(f"Failed to disable LLM recording: {e}")
    
    def get_stats(self):
        """Get recording statistics."""
        try:
            from llm_recorder import get_call_stats
            return get_call_stats()
        except Exception as e:
            logger.error(f"Failed to get recording stats: {e}")
            return {}
    
    def export_data(self, filename: str, **filters):
        """Export recorded data to file."""
        try:
            from llm_recorder import export_calls_to_csv
            export_calls_to_csv(filename, **filters)
            logger.info(f"Exported LLM call data to {filename}")
        except Exception as e:
            logger.error(f"Failed to export LLM call data: {e}")


def enable_recording_for_workflow(experiment_name: Optional[str] = None) -> bool:
    """
    Easy function to enable recording for the LangGraph workflow.
    
    Usage:
        from recording_config import enable_recording_for_workflow
        enable_recording_for_workflow("my_experiment")
    """
    config = RecordingConfig()
    return config.setup_recording(experiment_name)


def setup_recorded_extractor(provider: str = "openai", model: str = None, 
                           batch_size: int = 20, experiment_name: str = None):
    """
    Create a recorded version of the LLM extractor.
    
    This is a drop-in replacement for LLMTripleExtractor that includes recording.
    
    Usage:
        extractor = setup_recorded_extractor(
            provider="claude", 
            experiment_name="prompt_optimization_v1"
        )
        triples = extractor.extract_triples(messages)
    """
    from typing import List, Dict, Any
from recorded_llm_providers import RecordedLLMClient, RecordedLLMSegmentProcessor
    
    # Enable recording
    enable_recording_for_workflow(experiment_name)
    
    # Create recorded components
    llm_client = RecordedLLMClient(provider, model)
    processor = RecordedLLMSegmentProcessor(llm_client, batch_size)
    
    return RecordedLLMTripleExtractor(llm_client, processor)


class RecordedLLMTripleExtractor:
    """Main LLM-powered extraction coordinator with recording."""
    
    def __init__(self, llm_client, processor):
        self.llm_client = llm_client
        self.processor = processor
        
    def extract_triples(self, messages: List[Dict[str, Any]]) -> List['Triple']:
        """Extract triples using LLM APIs with full recording."""
        from collections import defaultdict
        import time
        
        logger.info(f"Starting recorded LLM-based extraction on {len(messages)} messages")
        
        # Group messages by segment for context-aware processing
        segments = defaultdict(list)
        for msg in messages:
            segments[msg['segment_id']].append(msg)
        
        logger.info(f"Processing {len(segments)} segments with recording enabled")
        
        all_triples = []
        processed_segments = 0
        
        for segment_id, segment_messages in segments.items():
            processed_segments += 1
            
            if processed_segments % 10 == 0:
                logger.info(f"Processed {processed_segments}/{len(segments)} segments")
                cost_summary = self.llm_client.get_cost_summary()
                logger.info(f"Current cost: ${cost_summary['total_cost_usd']}")
            
            # Sort messages by timestamp for context
            segment_messages.sort(key=lambda x: x['timestamp'])
            
            # Process segment with recording
            segment_triples = self.processor.process_segment(segment_messages, segment_id)
            all_triples.extend(segment_triples)
            
            # Rate limiting (be nice to APIs)
            time.sleep(0.1)
        
        # Final summary with recording stats
        cost_summary = self.llm_client.get_cost_summary()
        try:
            from llm_recorder import get_call_stats
            recording_stats = get_call_stats()
            logger.info(f"Recording stats: {recording_stats['total_calls']} calls recorded")
        except:
            pass
            
        logger.info(f"LLM extraction complete!")
        logger.info(f"Total: {len(all_triples)} triples from {len(messages)} messages")
        logger.info(f"Cost: ${cost_summary['total_cost_usd']} ({cost_summary['total_requests']} requests)")
        
        return all_triples
    
    def get_cost_summary(self):
        """Get cost and usage summary."""
        return self.llm_client.get_cost_summary()


# Global configuration instance
_config = RecordingConfig()


def get_recording_config() -> RecordingConfig:
    """Get the global recording configuration."""
    return _config