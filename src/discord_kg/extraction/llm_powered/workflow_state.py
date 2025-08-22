"""
LangGraph workflow state definition for Discord Knowledge Graph extraction pipeline.

This module defines the state structure that flows through the LangGraph workflow,
ensuring type safety and proper data handling between nodes.
"""

from typing import Dict, List, Any, Optional, TypedDict, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import datetime
import json


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy data types."""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer, np.floating, np.bool_)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)


class ProcessingStatus(Enum):
    """Processing status for workflow steps."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class MessageType(Enum):
    """Discord message types for classification."""
    QUESTION = "question"
    STRATEGY = "strategy"
    ANALYSIS = "analysis"
    ANSWER = "answer"
    ALERT = "alert"
    PERFORMANCE = "performance"
    DISCUSSION = "discussion"


@dataclass
class Triple:
    """Knowledge graph triple with metadata."""
    subject: str
    predicate: str
    object: str
    message_id: str
    segment_id: str
    timestamp: str
    confidence: float
    extraction_method: str = "llm"  # "llm", "rule_based", or "hybrid"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Ensure confidence is JSON serializable
        if hasattr(result['confidence'], 'item'):
            result['confidence'] = float(result['confidence'])
        return result


@dataclass
class ProcessingMetrics:
    """Metrics for tracking processing performance."""
    messages_processed: int = 0
    triples_extracted: int = 0
    api_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    processing_time_ms: int = 0
    error_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class NodeResult:
    """Result from a workflow node."""
    status: ProcessingStatus
    data: Any = None
    error: Optional[str] = None
    metrics: ProcessingMetrics = field(default_factory=ProcessingMetrics)
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())


class WorkflowState(TypedDict):
    """State that flows through the LangGraph workflow."""
    
    # Input data
    raw_messages: List[Dict[str, Any]]
    segment_id: Optional[str]
    batch_size: int
    
    # Configuration
    llm_provider: str  # "openai" or "claude"
    llm_model: Optional[str]
    config_path: Optional[str]
    
    # Processing state
    current_step: str
    processed_messages: List[Dict[str, Any]]
    message_segments: Dict[str, List[Dict[str, Any]]]
    classified_messages: Dict[str, List[Dict[str, Any]]]  # by message type
    
    # Results
    extracted_triples: List[Triple]
    qa_links: List[Triple]
    aggregated_results: List[Triple]
    
    # Node results
    preprocessing_result: Optional[NodeResult]
    classification_result: Optional[NodeResult]
    extraction_results: Dict[str, NodeResult]  # by message type
    qa_linking_result: Optional[NodeResult]
    aggregation_result: Optional[NodeResult]
    
    # Tracking and metrics
    overall_metrics: ProcessingMetrics
    cost_summary: Dict[str, Any]
    error_log: List[str]
    
    # Control flow
    should_skip_qa_linking: bool
    should_retry: bool
    max_retries: int
    current_retry: int


def create_initial_state(
    messages: List[Dict[str, Any]],
    llm_provider: str = "openai",
    llm_model: Optional[str] = None,
    batch_size: int = 20,
    config_path: Optional[str] = None,
    segment_id: Optional[str] = None
) -> WorkflowState:
    """Create initial workflow state."""
    
    return WorkflowState(
        # Input data
        raw_messages=messages,
        segment_id=segment_id,
        batch_size=batch_size,
        
        # Configuration
        llm_provider=llm_provider,
        llm_model=llm_model,
        config_path=config_path,
        
        # Processing state
        current_step="preprocessing",
        processed_messages=[],
        message_segments={},
        classified_messages={},
        
        # Results
        extracted_triples=[],
        qa_links=[],
        aggregated_results=[],
        
        # Node results
        preprocessing_result=None,
        classification_result=None,
        extraction_results={},
        qa_linking_result=None,
        aggregation_result=None,
        
        # Tracking and metrics
        overall_metrics=ProcessingMetrics(),
        cost_summary={},
        error_log=[],
        
        # Control flow
        should_skip_qa_linking=False,
        should_retry=False,
        max_retries=3,
        current_retry=0
    )


def update_state_metrics(state: WorkflowState, node_result: NodeResult) -> None:
    """Update overall state metrics from a node result."""
    overall = state["overall_metrics"]
    node_metrics = node_result.metrics
    
    overall.messages_processed += node_metrics.messages_processed
    overall.triples_extracted += node_metrics.triples_extracted
    overall.api_calls += node_metrics.api_calls
    overall.total_tokens += node_metrics.total_tokens
    overall.total_cost += node_metrics.total_cost
    overall.processing_time_ms += node_metrics.processing_time_ms
    overall.error_count += node_metrics.error_count


def log_error(state: WorkflowState, error_msg: str, step: str = None) -> None:
    """Log an error to the workflow state."""
    timestamp = datetime.datetime.now().isoformat()
    step_prefix = f"[{step}] " if step else ""
    formatted_error = f"{timestamp}: {step_prefix}{error_msg}"
    state["error_log"].append(formatted_error)


def get_messages_by_type(state: WorkflowState, message_type: Union[str, MessageType]) -> List[Dict[str, Any]]:
    """Get messages of a specific type from the classified messages."""
    if isinstance(message_type, MessageType):
        message_type = message_type.value
    
    return state["classified_messages"].get(message_type, [])


def has_questions_and_answers(state: WorkflowState) -> bool:
    """Check if the state has both questions and answers for Q&A linking."""
    questions = get_messages_by_type(state, MessageType.QUESTION)
    answers = get_messages_by_type(state, MessageType.ANSWER)
    return len(questions) > 0 and len(answers) > 0