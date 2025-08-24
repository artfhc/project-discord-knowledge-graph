"""
LangGraph workflow orchestrator for Discord Knowledge Graph extraction.

This module defines the main workflow using LangGraph, with conditional routing
and proper state management between processing nodes.
"""

import logging
from typing import Dict, Any, List, Optional, Literal
import time

try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    raise ImportError("LangGraph not installed. Run: pip install langgraph")

try:
    # Try relative imports first (when used as package)
    from .workflow_state import (
        WorkflowState, create_initial_state, ProcessingStatus, MessageType, 
        get_messages_by_type, has_questions_and_answers
    )
    from .nodes import (
        preprocessing_node, classification_node, 
        extract_question_node, extract_strategy_node, extract_analysis_node,
        extract_answer_node, extract_alert_node, extract_performance_node,
        extract_discussion_node, qa_linking_node, aggregation_node, cost_tracking_node
    )
except ImportError:
    # Fall back to direct imports (when running as script)
    from workflow_state import (
        WorkflowState, create_initial_state, ProcessingStatus, MessageType, 
        get_messages_by_type, has_questions_and_answers
    )
    from nodes import (
        preprocessing_node, classification_node, 
        extract_question_node, extract_strategy_node, extract_analysis_node,
        extract_answer_node, extract_alert_node, extract_performance_node,
        extract_discussion_node, qa_linking_node, aggregation_node, cost_tracking_node
    )

logger = logging.getLogger(__name__)


def should_run_extraction(state: WorkflowState, message_type: str) -> bool:
    """Determine if extraction should run for a specific message type."""
    messages = get_messages_by_type(state, message_type)
    return len(messages) > 0


def routing_node(state: WorkflowState) -> Literal[
    "extract_question", "extract_strategy", "extract_analysis", 
    "extract_answer", "extract_alert", "extract_performance", 
    "extract_discussion", "qa_linking", "aggregation"
]:
    """Route to the next extraction step based on available message types."""
    
    # Determine which message types have messages to process
    message_types_to_process = []
    
    # Check if user specified which types to extract
    allowed_types = state.get("extract_types")
    if allowed_types:
        allowed_types = set(allowed_types)
    
    for msg_type in [
        MessageType.QUESTION, MessageType.STRATEGY, MessageType.ANALYSIS,
        MessageType.ANSWER, MessageType.ALERT, MessageType.PERFORMANCE,
        MessageType.DISCUSSION
    ]:
        # Skip if user specified types and this type is not allowed
        if allowed_types and msg_type.value not in allowed_types:
            continue
            
        messages = get_messages_by_type(state, msg_type.value)
        if messages:
            message_types_to_process.append(msg_type.value)
    
    # Check what's already been processed
    processed_types = set(state["extraction_results"].keys())
    
    # Find next type to process
    for msg_type in message_types_to_process:
        if msg_type not in processed_types:
            return f"extract_{msg_type}"
    
    # All extractions done, check if we should do Q&A linking
    # Check if we should skip Q&A linking
    if state.get("should_skip_qa_linking", False):
        return "aggregation"
    
    # Check if we have both questions and answers
    if not has_questions_and_answers(state):
        return "aggregation"
    
    # Check if Q&A linking is already done
    if state.get("qa_linking_result") is not None:
        return "aggregation"
    
    return "qa_linking"


def qa_routing_node(state: WorkflowState) -> Literal["qa_linking", "aggregation"]:
    """Route to Q&A linking or skip to aggregation."""
    
    # Check if we should skip Q&A linking
    if state.get("should_skip_qa_linking", False):
        return "aggregation"
    
    # Check if we have both questions and answers
    if not has_questions_and_answers(state):
        state["should_skip_qa_linking"] = True
        return "aggregation"
    
    # Check if Q&A linking is already done
    if state.get("qa_linking_result") is not None:
        return "aggregation"
    
    return "qa_linking"


def create_extraction_workflow() -> StateGraph:
    """Create the main LangGraph workflow for triple extraction."""
    
    # Create the graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("preprocessing", preprocessing_node)
    workflow.add_node("classification", classification_node)
    workflow.add_node("routing", routing_node)
    
    # Add extraction nodes for each message type
    workflow.add_node("extract_question", extract_question_node)
    workflow.add_node("extract_strategy", extract_strategy_node)
    workflow.add_node("extract_analysis", extract_analysis_node)
    workflow.add_node("extract_answer", extract_answer_node)
    workflow.add_node("extract_alert", extract_alert_node)
    workflow.add_node("extract_performance", extract_performance_node)
    workflow.add_node("extract_discussion", extract_discussion_node)
    
    workflow.add_node("qa_linking", qa_linking_node)
    workflow.add_node("aggregation", aggregation_node)
    workflow.add_node("cost_tracking", cost_tracking_node)
    
    # Define workflow edges
    workflow.set_entry_point("preprocessing")
    workflow.add_edge("preprocessing", "classification")
    
    # Conditional routing directly from classification
    workflow.add_conditional_edges(
        "classification",
        routing_node,
        {
            "extract_question": "extract_question",
            "extract_strategy": "extract_strategy",
            "extract_analysis": "extract_analysis", 
            "extract_answer": "extract_answer",
            "extract_alert": "extract_alert",
            "extract_performance": "extract_performance",
            "extract_discussion": "extract_discussion",
            "qa_linking": "qa_linking",
            "aggregation": "aggregation"
        }
    )
    
    # All extraction nodes route back to classification for next conditional routing
    extraction_nodes = [
        "extract_question", "extract_strategy", "extract_analysis",
        "extract_answer", "extract_alert", "extract_performance", 
        "extract_discussion"
    ]
    
    for node in extraction_nodes:
        workflow.add_conditional_edges(
            node,
            routing_node,
            {
                "extract_question": "extract_question",
                "extract_strategy": "extract_strategy",
                "extract_analysis": "extract_analysis",
                "extract_answer": "extract_answer",
                "extract_alert": "extract_alert",
                "extract_performance": "extract_performance",
                "extract_discussion": "extract_discussion",
                "qa_linking": "qa_linking",
                "aggregation": "aggregation"
            }
        )
    
    # Q&A linking goes directly to aggregation when complete
    workflow.add_edge("qa_linking", "aggregation")
    workflow.add_edge("aggregation", "cost_tracking")
    workflow.add_edge("cost_tracking", END)
    
    return workflow


class ExtractionWorkflow:
    """High-level interface for running the extraction workflow."""
    
    def __init__(
        self, 
        llm_provider: str = "openai",
        llm_model: Optional[str] = None,
        batch_size: int = 20,
        config_path: Optional[str] = None,
        enable_checkpoints: bool = False,
        extract_types: Optional[List[str]] = None,
        should_skip_qa_linking: bool = False
    ):
        """
        Initialize the extraction workflow.
        
        Args:
            llm_provider: LLM provider ("openai" or "claude")
            llm_model: Specific model name
            batch_size: Batch size for processing
            config_path: Path to configuration file
            enable_checkpoints: Enable workflow checkpointing
            extract_types: Specific message types to extract
            should_skip_qa_linking: Skip Q&A linking step
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.batch_size = batch_size
        self.config_path = config_path
        self.enable_checkpoints = enable_checkpoints
        self.extract_types = extract_types
        self.should_skip_qa_linking = should_skip_qa_linking
        
        # Create workflow
        self.graph = create_extraction_workflow()
        
        # Compile with optional checkpointing
        if enable_checkpoints:
            memory = MemorySaver()
            self.app = self.graph.compile(checkpointer=memory)
        else:
            self.app = self.graph.compile()
        
        logger.info(f"Initialized extraction workflow with {llm_provider} provider")
    
    def run(
        self, 
        messages: List[Dict[str, Any]], 
        segment_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the complete extraction workflow.
        
        Args:
            messages: List of Discord messages to process
            segment_id: Optional segment ID for grouping
            thread_id: Optional thread ID for checkpointing
            
        Returns:
            Dict containing extracted triples and processing summary
        """
        start_time = time.time()
        
        logger.info(f"Starting extraction workflow for {len(messages)} messages")
        
        # Create initial state
        initial_state = create_initial_state(
            messages=messages,
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            batch_size=self.batch_size,
            config_path=self.config_path,
            segment_id=segment_id,
            extract_types=self.extract_types,
            should_skip_qa_linking=self.should_skip_qa_linking
        )
        
        # Run workflow
        config = {"thread_id": thread_id} if thread_id and self.enable_checkpoints else None
        
        try:
            final_state = self.app.invoke(initial_state, config=config)
            
            # Extract results
            total_time = time.time() - start_time
            
            result = {
                "status": "success",
                "triples": [triple.to_dict() for triple in final_state["aggregated_results"]],
                "processing_summary": {
                    "total_messages": len(messages),
                    "total_triples": len(final_state["aggregated_results"]),
                    "processing_time_seconds": round(total_time, 2),
                    "message_classification": final_state["classification_result"].data if final_state.get("classification_result") else {},
                    "extraction_results": {
                        msg_type: {
                            "status": result.status.value,
                            "triples_extracted": result.data.get("triples_extracted", 0) if result.data else 0,
                            "messages_processed": result.metrics.messages_processed
                        }
                        for msg_type, result in final_state["extraction_results"].items()
                    },
                    "qa_linking": {
                        "status": final_state["qa_linking_result"].status.value if final_state.get("qa_linking_result") else "skipped",
                        "links_created": len(final_state["qa_links"])
                    }
                },
                "cost_summary": final_state["cost_summary"],
                "errors": final_state["error_log"]
            }
            
            logger.info(f"Workflow completed successfully: {len(final_state['aggregated_results'])} triples in {total_time:.2f}s")
            return result
            
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"Workflow execution failed: {str(e)}"
            logger.error(error_msg)
            
            return {
                "status": "error",
                "error": error_msg,
                "triples": [],
                "processing_summary": {
                    "total_messages": len(messages),
                    "total_triples": 0,
                    "processing_time_seconds": round(total_time, 2)
                },
                "cost_summary": {},
                "errors": [error_msg]
            }
    
    def run_async(
        self, 
        messages: List[Dict[str, Any]],
        segment_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ):
        """
        Run the workflow asynchronously (returns an async generator).
        
        This allows for real-time monitoring of workflow progress.
        """
        # Create initial state
        initial_state = create_initial_state(
            messages=messages,
            llm_provider=self.llm_provider,
            llm_model=self.llm_model,
            batch_size=self.batch_size,
            config_path=self.config_path,
            segment_id=segment_id,
            extract_types=self.extract_types,
            should_skip_qa_linking=self.should_skip_qa_linking
        )
        
        # Run workflow with streaming
        config = {"thread_id": thread_id} if thread_id and self.enable_checkpoints else None
        
        return self.app.stream(initial_state, config=config)
    
    def get_workflow_visualization(self) -> str:
        """Get a text representation of the workflow graph."""
        try:
            # This would require additional dependencies for visualization
            return "Workflow visualization requires additional dependencies (graphviz, etc.)"
        except Exception as e:
            return f"Visualization not available: {e}"
    
    def validate_configuration(self) -> bool:
        """Validate the workflow configuration."""
        try:
            from .config import ConfigManager
            
            config_manager = ConfigManager(self.config_path)
            return config_manager.validate_config()
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


def run_extraction_pipeline(
    input_file: str,
    output_file: str,
    llm_provider: str = "openai",
    llm_model: Optional[str] = None,
    batch_size: int = 20,
    config_path: Optional[str] = None,
    extract_types: Optional[List[str]] = None,
    should_skip_qa_linking: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to run the extraction pipeline on a file.
    
    Args:
        input_file: Path to input JSONL file
        output_file: Path to output JSONL file
        llm_provider: LLM provider to use
        llm_model: Specific model name
        batch_size: Batch size for processing
        config_path: Path to configuration file
        extract_types: Specific message types to extract
        should_skip_qa_linking: Skip Q&A linking step
        
    Returns:
        Processing summary dictionary
    """
    import json
    try:
        from .workflow_state import NumpyEncoder
    except ImportError:
        from workflow_state import NumpyEncoder
    
    # Read messages
    messages = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))
    
    logger.info(f"Loaded {len(messages)} messages from {input_file}")
    
    # Run workflow
    workflow = ExtractionWorkflow(
        llm_provider=llm_provider,
        llm_model=llm_model,
        batch_size=batch_size,
        config_path=config_path,
        extract_types=extract_types,
        should_skip_qa_linking=should_skip_qa_linking
    )
    
    result = workflow.run(messages)
    
    if result["status"] == "success":
        # Write triples
        with open(output_file, 'w') as f:
            for triple in result["triples"]:
                f.write(json.dumps(triple, cls=NumpyEncoder) + '\n')
        
        # Write cost summary
        cost_file = output_file.replace('.jsonl', '_cost_summary.json')
        with open(cost_file, 'w') as f:
            json.dump(result["cost_summary"], f, indent=2)
        
        # Write processing summary
        summary_file = output_file.replace('.jsonl', '_processing_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(result["processing_summary"], f, indent=2)
        
        logger.info(f"Results written to {output_file}")
        logger.info(f"Cost summary: {cost_file}")
        logger.info(f"Processing summary: {summary_file}")
    
    return result