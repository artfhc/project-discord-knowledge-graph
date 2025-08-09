"""LLM-based message classification"""

from typing import Dict, Any, List, Literal
from enum import Enum

MessageType = Literal["question", "answer", "alert", "strategy"]

class MessageClassifier:
    """LLM-based message classification"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
    
    def classify_message(self, message: Dict[str, Any]) -> MessageType:
        """Classify message type using LLM"""
        # TODO: Implement LLM classification
        # - Use few-shot prompting
        # - Return one of: question, answer, alert, strategy
        pass
    
    def classify_batch(self, messages: List[Dict[str, Any]]) -> List[MessageType]:
        """Classify a batch of messages for efficiency"""
        # TODO: Batch LLM processing
        pass